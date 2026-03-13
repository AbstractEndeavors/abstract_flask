import ast,inspect,asyncio
from pathlib import Path
from typing import Iterable, List, Optional, Dict, Callable
from flask import Blueprint,request,jsonify
from .help_utils import offer_help
from ..request_utils import get_request_data,get_request_datas
from abstract_utilities import is_number,get_logFile,run_pruned_func,prune_inputs


# ============================================================
# Helpers
# ============================================================
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


def make_number(value):
    """Convert to int if numeric."""
    if is_number(value):
        if '.' in str(value):
            return float(value)
        return int(value)
    return value


def get_request_datas(req):
    """Wrapper that converts numeric fields."""
    data = get_request_data(req)
    return {k: make_number(v) for k, v in data.items()}


# ============================================================
# Endpoint Variant Builder
# ============================================================

def get_endpoints_ls(category: str, route_name: str, methods=None):
    """
    Build a pair of endpoint definitions:
        - /category/route
        - /category/route/
    """
    methods = methods or ["GET", "POST"]

    base_endpoint = f"{category}_{route_name}"
    base_rule = f"/{category}/{route_name}"

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
# ============================================================
# Registration Logic
# ============================================================

def register_route(bp: Blueprint, category: str, route_name: str, func: Callable,helper_funcs=None):
    logger = get_logFile("route_registrar")

    is_async = inspect.iscoroutinefunction(func)
    helper_funcs = helper_funcs or []
    async def async_route_func(*_, **__):
        data = get_request_datas(request)
        help_offered = offer_help(func,*helper_funcs, data=data, req=request)
        if help_offered:
            return help_offered

        try:
            logger.info(f"data == {data}")
            pruned = prune_inputs(func, **data)
            args, kwargs = normalize_pruned_inputs(pruned)
            response = await call_maybe_async(func, *args, **kwargs)
            if response is None:
                return jsonify({"error": "no response"}), 400
            return jsonify({"result": response}), 200

        except Exception as e:
            logger.exception(f"Error in {category}/{route_name}")
            return jsonify({"error": str(e)}), 500

    def sync_route_func(*_, **__):
        data = get_request_datas(request)
        help_offered = offer_help(func,*helper_funcs, data=data, req=request)
        if help_offered:
            return help_offered

        try:
            logger.info(f"data == {data}")
            pruned = prune_inputs(func, **data)
            logger.info(f"pruned_inputs == {pruned}")
            args, kwargs = normalize_pruned_inputs(pruned)
            response = func(*args, **kwargs)

            if response is None:
                return jsonify({"error": "no response"}), 400
            return jsonify({"result": response}), 200

        except Exception as e:
            logger.exception(f"Error in {category}/{route_name}")
            return jsonify({"error": str(e)}), 500

    view_func = async_route_func if is_async else sync_route_func

    for endpoint in get_endpoints_ls(category, route_name):
        bp.add_url_rule(view_func=view_func, **endpoint)

def register_category(bp: Blueprint, category: str, funcs: Dict[str, Callable],helper_funcs=None):
    helper_funcs = helper_funcs or []
    for route_name, func in funcs.items():
        register_route(bp, category, route_name, func,helper_funcs=helper_funcs)


def register_categories(bp: Blueprint, categories: Dict[str, Dict[str, Callable]]):
    for category, funcs in categories.items():
        register_category(bp, category, funcs)


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
