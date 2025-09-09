from abstract_paths import get_files_and_dirs
from abstract_utilities import read_from_file,make_list

def get_end_function(funcName,newFuncName,routName,offer_help=True):
    if offer_help:
       offer_help=f""" 
    help_offered = offer_help({funcName}, data=data, req=request)
    if help_offered:
        return help_offered\n"""
    else:
        offer_help = ""
    return f"""
@{routName}.route("/{funcName}", methods=["GET", "POST"], strict_slashes=False)
@{routName}.route("/{funcName}/", methods=["GET", "POST"], strict_slashes=False)
def {newFuncName}(*args,**kwargs):
    data = get_request_data(request)
    {offer_help}
    try:
        
        response = {funcName}(**data)
        if response == None:
            return jsonify({{"error": "no response"}}), 400
        return jsonify({{'result': response}}), 200
    except Exception as e:
        return jsonify({{'error': f"{{e}}"}}), 500"""
def get_ends(routName=None,url_prefix=None):
    routName = routName or 'flaskRoute_bp'
    if url_prefix:
        url_prefix = f",url_prefix='/{url_prefix}'"
    else:
        url_prefix = ""
    return ["""from abstract_flask import *
solar_units_bp = Blueprint('{routName}', __name__{urlPrefix})
logger = get_logFile('{routName}')"""]

def get_all_functions(
    texts,
    routName=None,
    url_prefix=None,
    take_locals=False
    ):
    lines = texts.split('\n')
    ends = get_ends(routName)
    for i,line in enumerate(lines):
        if line.startswith('def'):
            func_parts = line.split('(')
            func_def = func_parts[0]
            func_right = '('.join(func_parts[1:])
            func_name = func_def.split(' ')[1]
            if func_name.startswith('_') and not take_locals:
                break
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
    return ends
def generate_from_files(
    directory=None,
    files=None,
    directories=None,
    routName=None,
    url_prefix=None,
    take_locals=False):
    directories = directories or directory
    if directories:
        dirs,files = get_files_and_dirs(make_list(directories),
                           excluded_dirs = '__init__,node_modules'.split(','),
                           excluded_types=['compression'],
                           unallowed_exts=['pyc'],
                           allowed_exts=['.py'],
                           excluded_patterns=['__init__','node_modules'],
                                        recursive=True)
        
    files = make_list(files)

    pyDatas = []
    for file in files:
        pyDatas.append(read_from_file(file))
    pyData = '\n'.join(pyDatas)

    return get_all_functions(
        pyData,
        routName=routName,
        url_prefix=url_prefix,
        take_locals=take_locals
        )


