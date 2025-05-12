import os,sys,unicodedata,hashlib,json
from abstract_utilities import make_list,get_media_types,get_logFile
from multiprocessing import Process
from flask import (
    Blueprint,
    request,
    jsonify,
    send_file,
    current_app
)
from flask_cors import CORS
from .request_utils import (dump_if_json,
                            required_keys,
                            parse_request,
                            parse_and_return_json,
                            parse_and_spec_vars,
                            get_only_kwargs
                            )
from .network_utils import get_user_ip
from werkzeug.utils import secure_filename
def jsonify_it(obj):
    if isinstance(obj,dict):
        status_code = obj.get("status_code")
        return jsonify(obj),status_code
def get_bp(name, static_folder=None, static_url_path=None):
    # if they passed a filename, strip it down to the module name
    if os.path.isfile(name):
        basename = os.path.basename(name)
        name = os.path.splitext(basename)[0]

    bp_name = f"{name}_bp"
    logger  = get_logFile(bp_name)
    logger.info(f"Python path: {sys.path!r}")

    # build up only the kwargs they actually gave us
    bp_kwargs = {}
    if static_folder is not None:
        bp_kwargs['static_folder']    = static_folder
    if static_url_path is not None:
        bp_kwargs['static_url_path']  = static_url_path

    bp = Blueprint(
        bp_name,
        __name__,
        **bp_kwargs,
    )
    return bp, logger
