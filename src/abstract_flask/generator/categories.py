"""Category trees as data: merge several sections' ``ALL_CATEGORIES`` into one
tree and describe a tree as a JSON-able route catalog.

The nested category dict is the ONE route convention (see ``register_categories``):
dict nesting is the URL path, a ``<param>`` key is a path parameter, a callable
leaf is a GET+POST route answering ``{"result": ...}``, and a spec-dict leaf
(``{"view": fn, "methods": [...], "response": "native"|"result", "inputs":
"merged"|"path"}``) declares exact methods / a bare response on that same path.
A list of spec dicts on one key puts several method-specific views on one URL.

Because every section expresses its surface as that same tree, the sections
compose: ``merge_categories(brain.ALL_CATEGORIES, grading.ALL_CATEGORIES, ...)``
is the whole app's surface as one dict, which an arm (or the console) can read
with ``describe_categories`` without importing Flask internals.
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, Iterator


def spec(view: Callable, methods="GET,POST", *, response: str = "result", inputs: str = "merged",
         **extra: Any) -> dict:
    """A route-spec leaf, explicitly: ``spec(fn, "GET", response="native")`` is the
    dict ``{"view": fn, "methods": ["GET"], "response": "native", "inputs": "merged"}``.
    ``methods`` may be a comma-separated string or a list. Extra keys (``rule``,
    ``rules``, ``endpoint``, ``strict_slashes``) pass through."""
    if isinstance(methods, str):
        methods = [m.strip() for m in methods.split(",") if m.strip()]
    return {"view": view, "methods": [str(m).upper() for m in methods], "response": response,
            "inputs": inputs, **extra}


def _is_spec(value: Any) -> bool:
    return isinstance(value, dict) and "view" in value


def _is_leaf(value: Any) -> bool:
    return callable(value) or _is_spec(value) or isinstance(value, (list, tuple))


def iter_leaves(tree: dict, _prefix: str = "") -> Iterator[tuple[str, str, Any]]:
    """``(category, route_name, leaf)`` for every leaf, depth first, in source order."""
    for key, value in tree.items():
        key = str(key).strip("/")
        if _is_leaf(value):
            yield _prefix, key, value
        elif isinstance(value, dict):
            yield from iter_leaves(value, f"{_prefix}/{key}" if _prefix else key)
        else:
            where = f"{_prefix}/{key}" if _prefix else key
            raise TypeError(f"category entry {where!r} is {type(value).__name__}, expected dict or leaf")


def merge_categories(*trees: dict, name: str = "") -> dict:
    """Deep-merge category trees into one new tree (inputs are not modified).

    Two sections may share a node (both add leaves under ``llm``); they may NOT
    both define the same leaf path unless it is the very same object. A node in
    one tree and a leaf in another at the same key is a conflict too."""
    out: dict = {}
    for tree in trees:
        _merge_into(out, tree or {}, path=name)
    return out


def _merge_into(dst: dict, src: dict, path: str) -> None:
    for key, value in src.items():
        here = f"{path}/{key}" if path else str(key)
        new_node = isinstance(value, dict) and not _is_spec(value)
        if key not in dst:
            if new_node:
                dst[key] = {}
                _merge_into(dst[key], value, here)
            else:
                dst[key] = value
            continue
        cur = dst[key]
        cur_node = isinstance(cur, dict) and not _is_spec(cur)
        if cur_node and new_node:
            _merge_into(cur, value, here)
        elif cur is value:
            continue
        else:
            raise ValueError(f"category conflict at {here!r}: both trees define it")


def _view_of(leaf: Any) -> Callable:
    return leaf["view"] if _is_spec(leaf) else leaf


def _label(fn: Callable) -> str:
    mod = getattr(fn, "__module__", None) or "?"
    return f"{mod}:{getattr(fn, '__qualname__', getattr(fn, '__name__', '?'))}"


def describe_leaf(category: str, route_name: str, leaf: Any) -> dict:
    """One JSON-able row for a leaf: the path it serves and how it serves it."""
    path = "/" + "/".join(part for part in (category, route_name) if part)
    if _is_spec(leaf):
        methods = leaf.get("methods", ["GET", "POST"])
        methods = [methods] if isinstance(methods, str) else list(methods)
        rules = leaf.get("rules") or ([leaf["rule"]] if leaf.get("rule") else [path])
        rules = [r if isinstance(r, str) else r.get("rule") for r in ([rules] if isinstance(rules, str) else rules)]
        fn = leaf["view"]
        row = {"path": rules[0], "rules": rules, "methods": [m.upper() for m in methods], "kind": "spec",
               "inputs": leaf.get("inputs", "merged"), "response": leaf.get("response", "result")}
    else:
        fn = leaf
        row = {"path": path, "rules": [path, path + "/"], "methods": ["GET", "POST"], "kind": "callable",
               "inputs": "merged", "response": "result"}
    doc = inspect.getdoc(fn) or ""
    params = []
    try:
        for name, p in inspect.signature(fn).parameters.items():
            if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
                continue
            default = None if p.default is p.empty else p.default
            if not isinstance(default, (str, int, float, bool, type(None))):
                default = repr(default)          # sentinels and objects stay JSON-able
            params.append({"name": name, "default": default, "required": p.default is p.empty})
    except (TypeError, ValueError):
        pass
    row.update({"view": _label(fn), "doc": doc.splitlines()[0] if doc else "", "params": params})
    return row


def describe_categories(tree: dict) -> list[dict]:
    """The catalog of a tree: one row per leaf (a spec list yields one row each),
    sorted by path then methods. JSON-able; an arm can publish or consume it."""
    rows = []
    for category, route_name, leaf in iter_leaves(tree):
        leaves = leaf if isinstance(leaf, (list, tuple)) else [leaf]
        for one in leaves:
            rows.append(describe_leaf(category, route_name, one))
    rows.sort(key=lambda r: (r["path"], ",".join(r["methods"])))
    return rows


def category_paths(tree: dict) -> list[str]:
    """Every URL path a tree registers (one per leaf, bare form), sorted."""
    return sorted({row["path"] for row in describe_categories(tree)})


__all__ = ["spec", "iter_leaves", "merge_categories", "describe_leaf", "describe_categories", "category_paths"]
