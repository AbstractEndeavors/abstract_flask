import ast,inspect,asyncio,re
from pathlib import Path
from typing import Iterable, List, Optional, Dict, Callable
from flask import Blueprint,request,jsonify,Response
from werkzeug.exceptions import HTTPException
from .help_utils import offer_help
from ..request_utils import get_request_data,get_request_datas,make_number
from ..imports import is_number,get_logFile,prune_inputs


# ============================================================
# Helpers
# ============================================================
def is_flask_response(value):
    return isinstance(value, Response)

def _format_helper_funcs(helper_funcs: list[str]) -> str:
    """
    Format helper function names for code generation.
    """
    if not helper_funcs:
        return ""
    return ", " + ", ".join(helper_funcs)

async def call_maybe_async(func, *args,**kwargs):
    if inspect.iscoroutinefunction(func):
        return await func(*args,**kwargs)
    return func(*args,**kwargs)

def snake_to_camel(name: str) -> str:
    """Convert snake_case to lowerCamelCase."""
    parts = name.strip("_").split("_")
    if not parts:
        return name
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ============================================================
# Endpoint Variant Builder
# ============================================================

_PARAM = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")


def endpoint_name(category: str, route_name: str = "") -> str:
    """A Flask endpoint name for a category leaf: ``category_route``; URL
    converters ``<int:tid>`` / ``<path:key>`` collapse to the bare parameter
    name (``tid`` / ``key``) and dots become underscores (Flask forbids '.').
    Slashes from nested categories are kept, as they always were."""
    base = f"{category}_{route_name}" if category and route_name else (category or route_name or "index")
    return _PARAM.sub(r"\1", base).replace(".", "_")


def get_endpoints_ls(category: str, route_name: str, methods=None):
    """
    Build a pair of endpoint definitions:
        - /category/route
        - /category/route/
    """
    methods = methods or ["GET", "POST"]

    if route_name == "":
        # Index route: a nested node that is ALSO an endpoint. The empty-string
        # key means "this node itself" → URL is /{category} (no trailing segment).
        base_endpoint = category or "index"
        base_rule = f"/{category}" if category else "/"
    else:
        base_endpoint = f"{category}_{route_name}" if category else f"{route_name}"
        base_rule = f"/{category}/{route_name}" if category else f"/{route_name}"
    # Flask endpoint names may not contain '.'; the URL keeps the dot. This lets
    # dotted route names like `install.sh` ride the convention. A ``<param>``
    # segment (path identity declared in the tree) keeps only its bare name.
    base_endpoint = _PARAM.sub(r"\1", base_endpoint).replace(".", "_")

    # Two variants: plain and slash
    endpoints_js = {
        "endpoint": {
            "string": base_endpoint,
            "variants": ["", "_slash"],
        },
        "rule": {
            "string": base_rule,
            "variants": ["", "/"],
        }
    }

    endpoints_ls = []
    for key, values in endpoints_js.items():
        base = values["string"]
        variants = values["variants"]

        for i, suffix in enumerate(variants):
            if len(endpoints_ls) <= i:
                endpoints_ls.append({"methods": methods})

            endpoints_ls[i][key] = f"{base}{suffix}"

    return endpoints_ls

def normalize_pruned_inputs(pruned):
    """
    Normalize prune_inputs output into (args, kwargs)
    """
    if isinstance(pruned, dict):
        return (), pruned

    if isinstance(pruned, tuple):
        if len(pruned) == 2:
            args, kwargs = pruned
            return tuple(args or ()), dict(kwargs or {})
        if len(pruned) == 1:
            return (), dict(pruned[0])

    raise TypeError(f"Unsupported prune_inputs return type: {type(pruned)}")


def _register_spec(bp, category, route_name, spec):
    """Register an exact Flask route from a declarative category leaf.

    Callable leaves retain the original GET/POST and ``{"result": ...}``
    convention. A spec opts into an exact URL, methods, input handling and
    native Flask response semantics without a second blueprint mechanism.
    """
    allowed = {"view", "rule", "rules", "methods", "inputs", "response", "endpoint",
               "strict_slashes", "_shared_path"}
    unknown = set(spec) - allowed
    if unknown or not callable(spec.get("view")):
        raise ValueError(f"invalid route spec at {category}/{route_name}: {sorted(unknown)}")
    view = spec["view"]
    methods = spec.get("methods", ["GET", "POST"])
    if isinstance(methods, str):
        methods = [methods]
    methods = [str(method).upper() for method in methods]
    if not methods:
        raise ValueError("route methods cannot be empty")
    inputs = spec.get("inputs", "merged")
    response_mode = spec.get("response", "result")
    if inputs not in {"merged", "path"} or response_mode not in {"result", "native"}:
        raise ValueError("route inputs must be merged/path and response must be result/native")
    default_rule = "/" + "/".join(part for part in (category, route_name) if part)
    rules = spec.get("rules") or [spec.get("rule", default_rule)]
    if isinstance(rules, str):
        rules = [rules]
    if not rules or any(not isinstance(rule, (str, dict)) for rule in rules):
        raise ValueError("route rules must be absolute Flask URL rules")
    endpoint = spec.get("endpoint") or endpoint_name(category, route_name).strip("_").replace("/", "_")
    if spec.get("_shared_path") and not spec.get("endpoint"):
        # Several specs on one path (a list leaf): each needs its own endpoint
        # name, so the methods it answers become the suffix (…_get, …_post).
        endpoint += "_" + "_".join(m.lower() for m in methods)

    def arguments(path_values):
        if inputs == "path":
            return (), path_values
        data = get_request_datas(request)
        data.update(path_values)  # URL identity wins over a submitted field.
        return normalize_pruned_inputs(prune_inputs(view, **data))

    def render(value):
        if response_mode == "native":
            return value
        if value is None:
            return jsonify({"error": "no response"}), 400
        if is_flask_response(value):
            return value
        return jsonify({"result": value}), 200

    if inspect.iscoroutinefunction(view):
        async def handler(**path_values):
            args, kwargs = arguments(path_values)
            return render(await view(*args, **kwargs))
    else:
        def handler(**path_values):
            args, kwargs = arguments(path_values)
            return render(view(*args, **kwargs))

    for entry in rules:
        rule_spec = {"rule": entry} if isinstance(entry, str) else dict(entry)
        rule = rule_spec.pop("rule", None)
        if not isinstance(rule, str) or not rule.startswith("/"):
            raise ValueError("route rules must be absolute Flask URL rules")
        if set(rule_spec) - {"defaults"}:
            raise ValueError("route rule options only support defaults")
        bp.add_url_rule(rule, endpoint=endpoint, view_func=handler, methods=methods,
                        strict_slashes=spec.get("strict_slashes", False), **rule_spec)
# ============================================================
# Registration Logic
# ============================================================

def register_route(bp: Blueprint, category: str, route_name: str, func: Callable,helper_funcs=None):
    # Same convention, either framework: a non-Flask target (e.g. an aiohttp
    # web.Application / UrlDispatcher) is dispatched to the aiohttp twin.
    if not isinstance(bp, Blueprint):
        from .aiohttp_routes import register_route_aiohttp
        return register_route_aiohttp(bp, category, route_name, func, helper_funcs=helper_funcs)

    if isinstance(func, dict) and "view" in func:
        return _register_spec(bp, category, route_name, func)

    logger = get_logFile("route_registrar")

    is_async = inspect.iscoroutinefunction(func)
    helper_funcs = helper_funcs or []
    async def async_route_func(*_, **path_values):
        data = get_request_datas(request)
        data.update(path_values)  # a ``<param>`` key in the tree feeds the same-named kwarg
        help_offered = offer_help(func, *helper_funcs, data=data, req=request)

        if help_offered:
            return help_offered

        try:
            logger.info(f"data == {data}")

            pruned = prune_inputs(func, **data)
            args, kwargs = normalize_pruned_inputs(pruned)

            response = await call_maybe_async(func, *args, **kwargs)

            if response is None:
                return jsonify({"error": "no response"}), 400

            if is_flask_response(response):
                return response

            return jsonify({"result": response}), 200

        except HTTPException as e:
            return jsonify({"error": e.description}), e.code or 500
        except Exception as e:
            logger.exception(f"Error in {category}/{route_name}")
            return jsonify({"error": str(e)}), 500

    def sync_route_func(*_, **path_values):
        data = get_request_datas(request)
        data.update(path_values)  # a ``<param>`` key in the tree feeds the same-named kwarg
        help_offered = offer_help(func, *helper_funcs, data=data, req=request)

        if help_offered:
            return help_offered

        try:
            pruned = prune_inputs(func, **data)
            args, kwargs = normalize_pruned_inputs(pruned)

            response = func(*args, **kwargs)

            if response is None:
                return jsonify({"error": "no response"}), 400

            if is_flask_response(response):
                return response

            return jsonify({"result": response}), 200

        except HTTPException as e:
            return jsonify({"error": e.description}), e.code or 500
        except Exception as e:
            logger.exception(f"Error in {category}/{route_name}")
            return jsonify({"error": str(e)}), 500

    view_func = async_route_func if is_async else sync_route_func

    for endpoint in get_endpoints_ls(category, route_name):
        bp.add_url_rule(view_func=view_func, **endpoint)

def register_category(bp: Blueprint, category: str, funcs: Dict[str, Callable],helper_funcs=None):
    if not isinstance(bp, Blueprint):
        from .aiohttp_routes import register_category_aiohttp
        return register_category_aiohttp(bp, category, funcs, helper_funcs=helper_funcs)
    helper_funcs = helper_funcs or []
    for route_name, func in funcs.items():
        register_route(bp, category, route_name, func,helper_funcs=helper_funcs)


def flatten_categories(categories, _prefix: str = ""):
    """Walk a (possibly nested) category tree into ``(category, route_name, func)``.

    A dict value descends a level — its key (slash-joined) extends the category
    path; a callable value is a route — its key is the ``route_name`` and the
    accumulated path is the ``category``. So the flat 2-level form
    ``{"a/b": {"name": fn}}`` and the fully nested form
    ``{"a": {"b": {"name": fn}}}`` yield the SAME route, and ALL_CATEGORIES can be
    an ordinary nested JSON dict. A callable at the top level (empty accumulated
    category) becomes a single-segment route ``/name``."""
    for key, value in categories.items():
        key = str(key).strip("/")
        if callable(value) or isinstance(value, dict) and "view" in value:
            yield _prefix, key, value
        elif isinstance(value, (list, tuple)):
            # Several specs on ONE path (e.g. GET list + POST create on the same
            # URL): each entry is a spec leaf for this key.
            for i, spec in enumerate(value):
                if not (isinstance(spec, dict) and "view" in spec):
                    where = f"{_prefix}/{key}" if _prefix else key
                    raise TypeError(f"category entry {where!r}[{i}] must be a route spec dict")
                yield _prefix, key, {**spec, "_shared_path": True}
        elif isinstance(value, dict):
            path = f"{_prefix}/{key}" if _prefix else key
            yield from flatten_categories(value, path)
        else:
            where = f"{_prefix}/{key}" if _prefix else key
            raise TypeError(
                f"category entry {where!r} is {type(value).__name__}, expected dict or callable")


def register_categories(bp: Blueprint, categories):
    if not isinstance(bp, Blueprint):
        from .aiohttp_routes import register_categories_aiohttp
        return register_categories_aiohttp(bp, categories)
    for category, route_name, func in flatten_categories(categories):
        register_route(bp, category, route_name, func)


# ============================================================
# Auto Generator — Converts Python Files to Flask Endpoints
# ============================================================

def get_end_function(func_name: str, new_func_name: str, bp_name: str, is_async: bool, offer_help_block: bool = True,helper_funcs=None) -> str:
    async_kw = "async " if is_async else ""
    await_kw = "await " if is_async else ""
    helper_funcs = helper_funcs or []
    helper_args = _format_helper_funcs(helper_funcs)

    help_block = (
        f"    help_offered = offer_help({func_name}{helper_args}, data=data, req=request)\n"
        f"    if help_offered:\n"
        f"        return help_offered\n"
    ) if offer_help_block else ""

    return f'''@{bp_name}.route("/{func_name}", methods=["GET", "POST"], strict_slashes=False)
@{bp_name}.route("/{func_name}/", methods=["GET", "POST"], strict_slashes=False)
{async_kw}def {new_func_name}(*args, **kwargs):
    data = get_request_data(request)
{help_block}    try:
        response = {await_kw}{func_name}(**data)
        if response is None:
            return jsonify({{"error": "no response"}}), 400
        return jsonify({{"result": response}}), 200
    except Exception as e:
        return jsonify({{"error": str(e)}}), 500
'''

def get_ends(bp_name: str = "flaskRoute_bp", url_prefix: Optional[str] = None) -> List[str]:
    url_prefix_arg = f", url_prefix='/{url_prefix.lstrip('/')}'" if url_prefix else ""
    header = f'''from abstract_flask import *  # Provides Blueprint, request, jsonify, get_request_data, get_logFile, offer_help
# Auto-generated routes
{bp_name} = Blueprint('{bp_name}', __name__{url_prefix_arg})
logger = get_logFile('{bp_name}')
'''
    return [header]


def find_public_functions(source: str, take_locals: bool = False) -> Dict[str, bool]:
    funcs: Dict[str, bool] = {}
    tree = ast.parse(source)

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.name.startswith("_") and not take_locals:
                continue
            funcs[node.name] = False
        elif isinstance(node, ast.AsyncFunctionDef):
            if node.name.startswith("_") and not take_locals:
                continue
            funcs[node.name] = True

    return funcs

def generate_from_files(
    directory: Optional[str] = None,
    files: Optional[Iterable[str]] = None,
    bp_name: str = "flask_data_bp",
    url_prefix: Optional[str] = None,
    take_locals: bool = False,
    offer_help_block: bool = True,
    helper_funcs: bool = None
) -> str:

    paths: List[Path] = []
    helper_funcs = helper_funcs or []
    if directory:
        root = Path(directory)
        for p in root.rglob("*.py"):
            if ("__pycache__" in p.parts or "node_modules" in p.parts or p.name == "__init__.py"):
                continue
            paths.append(p)

    if files:
        paths.extend(Path(f) for f in files)

    pieces = get_ends(bp_name, url_prefix)

    for path in paths:
        src = read_text(path)

    funcs = find_public_functions(src, take_locals=take_locals)

    for fn, is_async in funcs.items():
        new_name = snake_to_camel(fn)
        pieces.append(
            get_end_function(
                fn,
                new_name,
                bp_name,
                is_async=is_async,
                offer_help_block=offer_help_block,
                helper_funcs=helper_funcs
            )
        )

    return "\n".join(pieces)
