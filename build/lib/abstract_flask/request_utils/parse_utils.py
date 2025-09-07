from .imports import get_only_kwargs
def parse_request(flask_request):
    """Parse incoming Flask request and return args and kwargs."""
    args = []
    kwargs = {}

    if flask_request.method == 'POST' and flask_request.is_json:
        # Parse from JSON body
        data = flask_request.get_json()
        args = data.get('args', [])
        kwargs = {key: value for key, value in data.items() if key != 'args'}
    else:
        # Parse from query parameters
        args = flask_request.args.getlist('args')
        kwargs = {key: value for key, value in flask_request.args.items() if key != 'args'}

    return args,kwargs
def parse_and_return_json(flask_request):
    args,kwargs = parse_request(flask_request)
    return {
        'args': args,
        'kwargs': kwargs
    }
def parse_and_spec_vars(flask_request,varList):
    if isinstance(varList,dict):
      varList = list(varList.keys())
    args,kwargs = parse_request(flask_request)
    kwargs = get_only_kwargs(varList,*args,**kwargs)
    return kwargs
