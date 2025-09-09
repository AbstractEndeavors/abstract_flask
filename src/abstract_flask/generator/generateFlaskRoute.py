def get_end_function(funcName,newFuncName,routName):
    return f"""
@{rout_name}.route("/{funcName}", methods=["GET", "POST"], strict_slashes=False)
@{rout_name}.route("/{funcName}/", methods=["GET", "POST"], strict_slashes=False)
def {newFuncName}(*args,**kwargs):
    data = get_request_data(request)
    try:
        response = {funcName}(**data)
        if response == None:
            return jsonify({{"error": "no response"}}), 400
        return jsonify({{'result': response}}), 200
    except Exception as e:
        return jsonify({{'error': f"{{e}}"}}), 500
    """
def get_ends(routName=None,url_prefix=None):
    routName = routName or 'flaskRoute_bp'
    if url_prefix:
        url_prefix = f",url_prefix='/{url_prefix}'"
    else:
        url_prefix = ""
    return ["""from abstract_flask import *
solar_units_bp = Blueprint('{routName}', __name__{urlPrefix})
logger = get_logFile('{routName}')"""]

def get_all_functions(text,routName=None,url_prefix=None):
    lines = texts.split('\n')
    ends = get_ends(routName)
    for i,line in enumerate(lines):
        if line.startswith('def'):
            func_parts = line.split('(')
            func_def = func_parts[0]
            func_right = '('.join(func_parts[1:])
            func_name = func_def.split(' ')[1]
            pieces = func_name.split('_')
            newName=''
            for piece in pieces:
                init= piece
                if newName:
                    init= piece.upper()
                    if len(piece)>0:
                        init = piece[0].upper()
                    if len(piece)>1:
                        init+=piece[1:].lower()
                newName+=init
            func_string = get_end_function(func_name,newName,routName)
            ends.append(func_string)
        lines[i] = line
   return ends
