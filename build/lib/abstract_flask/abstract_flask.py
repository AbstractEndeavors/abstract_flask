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
def register_bps(app,bp_list):
    for bp in bp_list:
        app.register_blueprint(bp)
    return app
from flask_cors import CORS
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
            ip_addr = request.remote_addr
            user = USER_IP_MGR.get_user_by_ip(ip_addr)
            record.remote_addr = ip_addr
            record.user = user
        else:
            record.remote_addr = None
            record.user = None
        return super().format(record)

def addHandler(app: Flask, *, name: str | None = None) -> Flask:
    if getattr(app, "_endpoints_registered", False):
        return app
    app._endpoints_registered = True

    name = name or os.path.splitext(os.path.basename(__file__))[0]

    # logger
    audit_hdlr = logging.FileHandler(f"{name}.log")
    audit_hdlr.setFormatter(RequestFormatter("%(asctime)s %(remote_addr)s %(user)s %(message)s"))
    app.logger.addHandler(audit_hdlr)

    # /api/endpoints
    @app.route("/api/endpoints", methods=["OPTIONS", "GET", "POST"])
    def getEnds():
        endpoints = [
            (rule.rule, ", ".join(sorted(rule.methods - {"HEAD", "OPTIONS"})))
            for rule in app.url_map.iter_rules()
        ]
        return jsonify(sorted(endpoints)), 200

    return app

def get_Flask_app(*, name="abstract_flask", bp_list=None, allowed_origins=None, **kwargs):
    if "allowed_origins" in kwargs:
        allowed_origins = kwargs.pop("allowed_origins")

    app = Flask(name, **kwargs)

    # Ensure CORS is applied globally
    CORS(
        app,
        resources={r"/*": {"origins": allowed_origins or "*"}},
        supports_credentials=True,
        allow_headers=["Authorization", "Content-Type"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    app = addHandler(app, name=name)
    app = register_bps(app, bp_list or [])

    return app
def main_flask_start(app, key_head="", env_path=None, **kwargs):
    key_head = key_head.upper()
    KEY_VALUES = {
        "DEBUG": {"type": bool, "default": True},
        "HOST": {"type": str, "default": "0.0.0.0"},
        "PORT": {"type": int, "default": 5000},
    }
    for key, values in KEY_VALUES.items():
        nu_key = f"{key_head}_{key}"
        typ = values["type"]
        default = values["default"]
        KEY_VALUES[key] = typ(get_env_value(path=env_path, key=nu_key) or default)

    app.run(
        debug=KEY_VALUES["DEBUG"],
        host=KEY_VALUES["HOST"],
        port=KEY_VALUES["PORT"],
    )
