# generator.py
import ast
import inspect
from pathlib import Path
from typing import Iterable, List, Optional

# --- small helpers ---
def snake_to_camel(name: str) -> str:
    parts = name.strip("_").split("_")
    if not parts:
        return name
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")

# --- route template builders ---
def get_end_function(func_name: str, new_func_name: str, bp_name: str, offer_help_block: bool = True) -> str:
    help_snippet = (
        f"    help_offered = offer_help({func_name}, data=data, req=request)\n"
        f"    if help_offered:\n"
        f"        return help_offered\n"
    ) if offer_help_block else ""

    return f'''@{bp_name}.route("/{func_name}", methods=["GET", "POST"], strict_slashes=False)
@{bp_name}.route("/{func_name}/", methods=["GET", "POST"], strict_slashes=False)
def {new_func_name}(*args, **kwargs):
    data = get_request_data(request)
{help_snippet}    try:
        response = {func_name}(**data)
        if response is None:
            return jsonify({{"error": "no response"}}), 400
        return jsonify({{"result": response}}), 200
    except Exception as e:
        return jsonify({{"error": str(e)}}), 500
'''

def get_ends(bp_name: str = "flaskRoute_bp", url_prefix: Optional[str] = None) -> List[str]:
    url_prefix_arg = f", url_prefix='/{url_prefix.lstrip('/')}'" if url_prefix else ""
    header = f'''from abstract_flask import *  # must provide Blueprint, request, jsonify, get_request_data, get_logFile, offer_help
# Auto-generated routes
{bp_name} = Blueprint('{bp_name}', __name__{url_prefix_arg})
logger = get_logFile('{bp_name}')
'''
    return [header]

# --- AST-driven function finder ---
def find_public_functions(source: str, take_locals: bool = False) -> List[str]:
    """
    Return a list of top-level function names in source.
    Skips dunder/private (starting with '_') unless take_locals=True.
    """
    names: List[str] = []
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            name = node.name
            if name.startswith("_") and not take_locals:
                continue
            names.append(name)
    return names

# --- main generation API ---
def generate_from_files(
    directory: Optional[str] = None,
    files: Optional[Iterable[str]] = None,
    bp_name: str = "flask_data_bp",
    url_prefix: Optional[str] = None,
    take_locals: bool = False,
    offer_help_block: bool = True,
) -> str:
    paths: List[Path] = []
    if directory:
        root = Path(directory)
        for p in root.rglob("*.py"):
            if ("__pycache__" in p.parts or "node_modules" in p.parts or p.name == "__init__.py"):
                continue
            paths.append(p)
    if files:
        paths += [Path(f) for f in files]

    pieces = get_ends(bp_name, url_prefix)

    for path in paths:
        src = read_text(path)
        func_names = find_public_functions(src, take_locals=take_locals)
        for fn in func_names:
            new_name = snake_to_camel(fn)
            pieces.append(get_end_function(fn, new_name, bp_name, offer_help_block=offer_help_block))

    return "\n".join(pieces)
