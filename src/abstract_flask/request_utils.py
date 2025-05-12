from abstract_utilities.json_utils import (json,
                                           get_only_kwargs,
                                           get_desired_key_values,
                                           makeParams,
                                           dump_if_json,
                                           make_list)
def get_proper_kwargs(strings, **kwargs):
    # Convert the provided strings to lowercase for case-insensitive matching
    strings_lower = [string.lower() for string in strings]
    matched_keys = {}  # This will store matched keys and their corresponding values
    
    remaining_kwargs = kwargs.copy()  # Copy the kwargs so we can remove matched keys

    # Exact matching: Find exact lowercase matches first and remove them
    for string in strings_lower:
        for key in list(remaining_kwargs):  # Iterate over a copy of the keys
            if key.lower() == string:
                matched_keys[key] = remaining_kwargs.pop(key)  # Remove matched key from remaining_kwargs
                break

    # Partial matching: Check for keys that contain the string and remove them
    for string in strings_lower:
        for key in list(remaining_kwargs):  # Iterate over a copy of the keys
            if string in key.lower():
                matched_keys[key] = remaining_kwargs.pop(key)  # Remove matched key from remaining_kwargs
                break

    # Return the first matched value or None if no match
    if matched_keys:
        return list(matched_keys.values())[0]
    
    # Log or raise an error if no key was found for debugging
    print(f"No matching key found for: {strings} in {kwargs.keys()}")
    return None
async def async_makeParams(*arg,**kwargs):
   return makeParams(*arg,**kwargs)

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
   

def required_keys(keys,req,defaults=None):
    defaults = defaults or {}
    datas = get_request_data(req)
    for key in keys:
        value = datas.get(key) or defaults.get(key)
        if not value:
            return {"error": f"could not find {key} in values","status_code":400}
    return datas
def get_request_data(req):
    """Retrieve JSON data (for POST) or query parameters (for GET)."""
    if req.method == 'POST':
        return req.json
    else:
        return req.args.to_dict()

def execute_request(keys,req,func=None,desired_keys=None,defaults=None):
   
    try:
        datas = required_keys(keys,req,defaults=defaults)
        if datas and isinstance(datas,dict) and datas.get('error'):
            return datas
        desired_key_values = get_desired_key_values(obj=datas,keys=desired_keys,defaults=defaults)
        result = func(**desired_key_values)
        return {"result": result,"status_code":200}
    except Exception as e:
        return {"error": f"{e}","status_code":500}
