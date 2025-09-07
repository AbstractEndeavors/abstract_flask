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


from flask_cors import CORS
from abstract_utilities import make_list,get_media_types,get_logFile
from multiprocessing import Process
from flask import *
from abstract_queries import USER_IP_MGR
from .file_utils import *
from .request_utils import *
from .network_utils import *
from werkzeug.utils import secure_filename
import os,sys,unicodedata,hashlib,json,logging
from abstract_security import get_env_value    
logger = get_logFile('abstract_flask')
def get_from_kwargs(keys,**kwargs):
    output_js = {}
    for key in keys:
        if key in kwargs:
            output_js[key]= kwargs.get(key)
            del kwargs[key]
    return output_js,kwargs
def get_name(name=None,abs_path=None):
    if os.path.isfile(name):
        basename = os.path.basename(name)
        name = os.path.splitext(basename)[0]
    abs_path = abs_path or __name__
    return name,abs_path

def jsonify_it(obj):
    if isinstance(obj,dict):
        status_code = obj.get("status_code")
        return jsonify(obj),status_code

def get_bp(name=None,abs_path=None, **bp_kwargs):
    # if they passed a filename, strip it down to the module name
    name,abs_path = get_name(name=name,abs_path=abs_path)
    bp_name = f"{name}_bp"
    logger  = get_logFile(bp_name)
    logger.info(f"Python path: {sys.path!r}")
    # build up only the kwargs they actually gave us
    bp = Blueprint(
        bp_name,
        abs_path,
        **bp_kwargs,
    )
    return bp, logger
class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            # `request` is the current flask.Request proxy
            ip_addr = get_ip_addr(req=request)
            user = USER_IP_MGR.get_user_by_ip(ip_addr)
            record.remote_addr = ip_addr
            record.user = user
        else:
            record.remote_addr = None
            record.user = None
        return super().format(record)
def addHandler(app: Flask, *, name: str | None = None) -> Flask:
    # ---- short-circuit if we've already been here ---------
    if getattr(app, "_endpoints_registered", False):
        return app
    app._endpoints_registered = True               # mark as done
    # -------------------------------------------------------

    name = name or os.path.splitext(os.path.basename(__file__))[0]
    
    # ---- audit logger -------------------------------------
    audit_path  = f"{name}.log"
    audit_fmt   = RequestFormatter(
        "%(asctime)s %(remote_addr)s %(user)s %(message)s"
    )
    audit_hdlr  = logging.FileHandler(audit_path)
    audit_hdlr.setFormatter(audit_fmt)
    app.logger.addHandler(audit_hdlr)

    # ---- request hooks ------------------------------------
    @app.before_request
    def record_ip_for_authenticated_user():
        if getattr(request, "user", None):
            user = get_user_by_username(request.user["username"])
            if user:
                log_user_ip(user["id"], request.remote_addr)

    # ---- single, multi-method route -----------------------
    if "getEnds" not in app.view_functions:        # extra belt-and-braces
        @app.route("/api/endpoints", methods=["GET", "POST"])
        def getEnds():
            endpoints = [
                (rule.rule, ", ".join(sorted(rule.methods - {"HEAD", "OPTIONS"})))
                for rule in app.url_map.iter_rules()
            ]
            return jsonify(sorted(endpoints)), 200

    return app

def register_bps(app,bp_list):
    for bp in bp_list:
        app.register_blueprint(bp)
    return app
def get_Flask_app(*args,**kwargs):
    """Quart app factory."""
    keys = ['name','bp_list']
    values , kwargs = get_from_kwargs(keys,**kwargs)
    name = values.get('name')
    bp_list = values.get('bp_list')
    for arg in args:
        if not name and not isinstance(arg,list):
            name = arg
        elif not bp_list:
            bp_list = arg
    bp_list = bp_list or []
    name,abs_path = get_name(name)
    app = Flask(name,**kwargs)
    app = addHandler(app,name=name)
    app = register_bps(app,bp_list)
    return app
def main_flask_start(app,key_head = '',env_path=None,**kwargs):
    key_head = key_head.upper()
    KEY_VALUS = {"DEBUG":{"type":bool,"default":True},
             "HOST":{"type":str,"default":'0.0.0.0'},
             "PORT":{"type":int,"default":True}}
    for key,values in KEY_VALUS.iteems():
        nu_key = f"{key_head}_{key}"
        typ = values.get("type")
        default = values.get("default")
        KEY_VALUS[key]=typ(get_env_value(path=env_path,key=nu_key) or default)
        app.run(debug=KEY_VALUS["DEBUG"], host=KEY_VALUS["HOST"], port=KEY_VALUS["PORT"])

