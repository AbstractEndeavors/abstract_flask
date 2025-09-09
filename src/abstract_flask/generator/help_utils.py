import inspect
from flask import jsonify

def offer_help(*functions, data=None, req=None):
    """
    Inspect function signatures and return JSON help if 'help' is in request data.
    """
    if not data and not req:
        return None

    # Collect request data
    data = data or get_request_data(req)

    if "help" not in data:
        return None  # only respond with help if requested

    nuParams = {}
    for fn in functions:
        func_name = fn.__name__  # <-- get the function name
        sig = inspect.signature(fn)

        nuParams[func_name] = {
            "doc": inspect.getdoc(fn),
            "params": []
        }

        for name, param in sig.parameters.items():
            nuParams[func_name]["params"].append({
                "name": name,
                "default": None if param.default is inspect._empty else param.default,
                "annotation": None if param.annotation is inspect._empty else str(param.annotation)
            })

    return jsonify(nuParams), 200
