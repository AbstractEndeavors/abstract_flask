"""aiohttp twin of :mod:`generateFlaskRoute`.

Registers a category dict of plain functions as aiohttp routes with the *same*
convention Flask uses, so a caller writes the identical line regardless of
framework::

    register_categories(math_bp, ALL_CATEGORIES)   # Flask blueprint
    register_categories(app, ALL_CATEGORIES)        # aiohttp web.Application

Each ``{category: {route_name: fn}}`` entry becomes ``/category/route_name`` and
``/category/route_name/`` for GET+POST, with a handler that merges the request
data (path params + query + JSON body), offers ``?help``/``{"help": ...}``,
prunes the inputs to ``fn``'s signature, calls it (awaiting a coroutine), and
returns ``{"result": ...}`` — or ``{"error": ...}`` with a 4xx/5xx — exactly like
the Flask path.

``aiohttp`` is imported at module top because this *is* the aiohttp module; the
package ``generator/__init__`` imports it guardedly and the dispatch in
:mod:`generateFlaskRoute` imports it lazily, so Flask-only installs without
aiohttp are unaffected.
"""
import inspect
from typing import Callable, Dict

from aiohttp import web

from .help_utils import build_help_payload, _help_requested
from .generateFlaskRoute import normalize_pruned_inputs
from ..imports import get_logFile, prune_inputs

logger = get_logFile("aiohttp_route_registrar")

_METHODS = ("GET", "POST")


async def _request_data(request) -> dict:
    """Merge path match_info, query string, and JSON body into one dict — the
    aiohttp analogue of ``get_request_datas(flask_request)``. Body wins over
    query, query wins over path params."""
    data: dict = {}
    try:
        data.update(dict(request.match_info))
    except Exception:  # noqa: BLE001
        pass
    try:
        data.update({k: v for k, v in request.query.items()})
    except Exception:  # noqa: BLE001
        pass
    if getattr(request, "can_read_body", False):
        try:
            body = await request.json()
            if isinstance(body, dict):
                data.update(body)
        except Exception:  # noqa: BLE001 — a non-JSON / empty body is simply ignored
            pass
    return data


def _make_handler(category: str, route_name: str, func: Callable, helper_funcs):
    is_async = inspect.iscoroutinefunction(func)
    helper_funcs = helper_funcs or []
    try:
        _params = list(inspect.signature(func).parameters)
    except (TypeError, ValueError):
        _params = []
    # A RAW aiohttp handler takes the aiohttp request (named `request`/`req`) as
    # its first parameter — it reads the request itself, including the app state
    # in `request.app[...]`, and returns a web.Response / web.StreamResponse. We
    # pass the request straight through and return its result unchanged. This lets
    # existing aiohttp views be registered under the same category-dict convention
    # as pure functions, without rewriting their body/state access.
    raw_request = bool(_params) and _params[0] in ("request", "req")

    async def handler(request):
        try:
            if raw_request:
                response = await func(request) if is_async else func(request)
            else:
                data = await _request_data(request)
                if _help_requested(data=data):
                    return web.json_response(build_help_payload(func, *helper_funcs))
                logger.info("data == %s", data)
                pruned = prune_inputs(func, **data)
                args, kwargs = normalize_pruned_inputs(pruned)
                response = await func(*args, **kwargs) if is_async else func(*args, **kwargs)

            if response is None:
                return web.json_response({"error": "no response"}, status=400)

            # web.Response is a subclass of web.StreamResponse → both pass through.
            if isinstance(response, web.StreamResponse):
                return response

            return web.json_response({"result": response})

        except Exception as e:  # noqa: BLE001
            logger.exception("Error in %s/%s", category, route_name)
            return web.json_response({"error": str(e)}, status=500)

    return handler


def _resolve_router(target):
    """Accept a ``web.Application`` or a ``web.UrlDispatcher`` (``app.router``)."""
    if isinstance(target, web.Application):
        return target.router
    return target  # a UrlDispatcher, or anything exposing add_route(method, path, handler)


def register_route_aiohttp(target, category: str, route_name: str, func: Callable, helper_funcs=None):
    router = _resolve_router(target)
    handler = _make_handler(category, route_name, func, helper_funcs)
    if route_name == "":                       # index route: the node itself → /{category}
        base = f"/{category}" if category else "/"
    else:
        base = f"/{category}/{route_name}" if category else f"/{route_name}"
    for rule in (base, base + "/"):
        for method in _METHODS:
            router.add_route(method, rule, handler)


def register_category_aiohttp(target, category: str, funcs: Dict[str, Callable], helper_funcs=None):
    for route_name, func in funcs.items():
        register_route_aiohttp(target, category, route_name, func, helper_funcs=helper_funcs)


def register_categories_aiohttp(target, categories):
    # Supports flat {"a/b": {"name": fn}} and nested {"a": {"b": {"name": fn}}}.
    from .generateFlaskRoute import flatten_categories
    for category, route_name, func in flatten_categories(categories):
        register_route_aiohttp(target, category, route_name, func)


def get_aiohttp_app(routes=None, categories=None, middlewares=None, on_startup=None):
    """Twin of ``get_Flask_app``: build a ``web.Application`` and register category
    dicts on it. ``categories`` is an ALL_CATEGORIES dict; ``routes`` may be a module
    exposing ``ALL_CATEGORIES``. ``middlewares``/``on_startup`` are passed through."""
    app = web.Application(middlewares=list(middlewares or []))
    for cb in (on_startup or []):
        app.on_startup.append(cb)

    cats: dict = {}
    if categories:
        cats.update(categories)
    if routes is not None:
        found = getattr(routes, "ALL_CATEGORIES", None)
        if isinstance(found, dict):
            cats.update(found)
    if cats:
        register_categories_aiohttp(app, cats)
    return app
