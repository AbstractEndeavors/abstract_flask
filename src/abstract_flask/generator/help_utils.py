import inspect
from flask import jsonify
from ..request_utils import get_request_data


def _help_requested(data=None, req=None):
    """True when the caller asked for help — either ``{"help": ...}`` in the parsed
    data or a ``?help`` query param on a Flask request. Framework-neutral: ``req``
    is optional and only consulted when given."""
    if data and "help" in data:
        return True
    if req is not None:
        try:
            return req.args.get("help") is not None
        except Exception:
            return False
    return False


def build_help_payload(*functions):
    """Framework-neutral help payload: {fn_name: {doc, params[]}} for each callable.
    Returns a plain dict so either Flask (jsonify) or aiohttp (web.json_response)
    can serialize it."""
    help_payload = {}
    for fn in functions:
        # Only process actual callables
        if not callable(fn):
            continue

        fn_name = getattr(fn, "__name__", "<unknown>")
        sig = inspect.signature(fn)
        doc = inspect.getdoc(fn)

        params_list = []

        for name, param in sig.parameters.items():
            default_val = None if param.default is inspect._empty else param.default
            annotation = None if param.annotation is inspect._empty else str(param.annotation)

            params_list.append({
                "name": name,
                "default": default_val,
                "annotation": annotation
            })

        help_payload[fn_name] = {
            "doc": doc,
            "params": params_list
        }

    return help_payload


def offer_help(*functions, data=None, req=None):
    """
    Returns a JSON help response when the user requests '?help' or {"help": ...}.
    Inspects each function signature and provides docstrings + parameter metadata.
    """

    # no request context or data → nothing to offer
    if data is None and req is None:
        return None

    # normalize data
    data = data or get_request_data(req)

    if not _help_requested(data=data, req=req):
        return None

    return jsonify(build_help_payload(*functions)), 200
