from .request_utils import get_request_data,extract_request_data
from .imports import makeParams,get_desired_key_values
async def async_makeParams(*arg,**kwargs):
   return makeParams(*arg,**kwargs)
def required_keys(keys,req,defaults=None):
    defaults = defaults or {}
    datas = get_request_data(req)
    for key in keys:
        value = datas.get(key) or defaults.get(key)
        if not value:
            return {"error": f"could not find {key} in values","status_code":400}
    return datas

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
from typing import Any, Dict, Type, Union, Tuple

def try_type(obj: Any, typ: Type) -> Tuple[Any, bool]:
    """Attempt to convert obj to the specified type."""
    try:
        return typ(obj), True
    except (ValueError, TypeError):
        return obj, False

def process_args(args: list, typ: Type) -> Tuple[list, Any, bool]:
    """Extract and convert the first non-None argument to the specified type."""
    if not args:
        return args, None, False
    
    # Find first non-None argument
    for i, arg in enumerate(args):
        if arg is not None:
            remaining_args = args[i+1:]  # Skip the processed arg
            if isinstance(arg, typ):
                return remaining_args, arg, True
            converted_arg, success = try_type(arg, typ)
            return remaining_args, converted_arg, success
    
    return args, None, False

def get_spec_kwargs(var_types: Dict[str, Dict[str, Any]], args: list = None, **kwargs) -> Dict[str, Any]:
    """
    Process arguments and keyword arguments based on specified types and default values.
    
    Args:
        var_types: Dictionary mapping keys to {"value": default, "type": type}.
        args: Optional list of positional arguments.
        kwargs: Keyword arguments to process.
    
    Returns:
        Dictionary of processed key-value pairs.
    """
    if args is None:
        args = []
    
    result = {}
    args = args.copy()  # Avoid modifying input list
    
    for key, spec in var_types.items():
        default_value = spec.get("value")
        target_type = spec.get("type")
        
        # Check if key is in kwargs
        if key in kwargs:
            value = kwargs[key]
            if isinstance(value, target_type):
                result[key] = value
            else:
                converted_value, success = try_type(value, target_type)
                result[key] = converted_value if success else default_value
        else:
            # Try to process from args
            args, value, success = process_args(args, target_type)
            result[key] = value if success else default_value
    
    return result
def get_args_jwargs_user_req(req,var_types={}):
   result = extract_request_data(req)
   username = result.get('user')
   args = result.get('args', [])
   data = result.get('json',{})
   return data,args,username
