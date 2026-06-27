import inspect
from flask import jsonify
from ..request_utils import get_request_data


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

    # detect help flag in JSON or GET query params
    help_requested = (
        ("help" in data) or
        (req is not None and req.args.get("help") is not None)
    )
    if not help_requested:
        return None

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

    return jsonify(help_payload), 200
