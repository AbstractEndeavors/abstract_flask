import inspect
import logging
import os
import sys

from flask import Blueprint, Flask, jsonify, request, has_request_context
from flask_cors import CORS
from werkzeug.utils import secure_filename

from abstract_utilities import make_list, get_media_types, get_logFile, eatAll
from abstract_security import get_env_value

logger = get_logFile("abstract_flask")


# ──────────────────────────────────────────────────────────
# Blueprint helpers
# ──────────────────────────────────────────────────────────

def get_name(name=None, abs_path=None):
    if name and os.path.isfile(name):
        basename = os.path.basename(name)
        name = os.path.splitext(basename)[0]
    abs_path = abs_path or __name__
    return name, abs_path


def get_bp(name=None, abs_path=None, **bp_kwargs):
    name, abs_path = get_name(name=name, abs_path=abs_path)
    bp_name = f"{name}_bp"
    bp_logger = get_logFile(bp_name)
    bp_logger.info(f"Python path: {sys.path!r}")
    bp = Blueprint(bp_name, abs_path, **bp_kwargs)
    return bp, bp_logger


def _discover_blueprints(routes_module, url_prefix=None):
    """Scan a routes module for objects named *_bp that are Blueprints."""
    bps = []
    for attr_name, obj in vars(routes_module).items():
        if attr_name.endswith("_bp") and isinstance(obj, Blueprint):
            if url_prefix:
                bps.append((obj, f"/{url_prefix}/"))
            else:
                bps.append(obj)
    return bps


def _register_blueprints(app, bp_list):
    """
    bp_list items can be:
      - Blueprint
      - (Blueprint, "/prefix")
    """
    for entry in bp_list or []:
        if isinstance(entry, tuple):
            bp, prefix = entry
            app.register_blueprint(bp, url_prefix=prefix)
        else:
            app.register_blueprint(entry)
    return app


# ──────────────────────────────────────────────────────────
# Request-aware log formatter
# ──────────────────────────────────────────────────────────

class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            record.remote_addr = request.remote_addr
            record.user = None
        else:
            record.remote_addr = None
            record.user = None
        return super().format(record)


def _attach_audit_log(app, *, name=None):
    """Add a request-aware file handler to the app logger. Idempotent."""
    if getattr(app, "_audit_log_attached", False):
        return
    app._audit_log_attached = True

    log_name = name or os.path.splitext(os.path.basename(__file__))[0]
    handler = logging.FileHandler(f"{log_name}.log")
    handler.setFormatter(
        RequestFormatter("%(asctime)s %(remote_addr)s %(user)s %(message)s")
    )
    app.logger.addHandler(handler)


# ──────────────────────────────────────────────────────────
# Introspection endpoints
# ──────────────────────────────────────────────────────────

def _add_endpoint_inspector(app, prefix=None):
    """
    /endpoints            → all endpoints (always)
    /<prefix>/endpoints   → filtered to prefix (when given)
    """
    if "global_endpoint_inspector" not in app.view_functions:

        @app.route("/endpoints", endpoint="global_endpoint_inspector", methods=["GET"])
        def list_all_endpoints():
            output = []
            for rule in app.url_map.iter_rules():
                if rule.endpoint == "static":
                    continue
                methods = sorted(rule.methods - {"HEAD", "OPTIONS"})
                output.append({
                    "endpoint": rule.endpoint,
                    "url": str(rule),
                    "methods": methods,
                })
            return jsonify(sorted(output, key=lambda x: x["url"])), 200

    if not prefix:
        return

    normalized = prefix.strip("/")
    ep_name = f"{normalized}_endpoint_inspector"

    if ep_name not in app.view_functions:

        @app.route(f"/{normalized}/endpoints", endpoint=ep_name, methods=["GET"])
        def list_prefixed_endpoints():
            output = []
            for rule in app.url_map.iter_rules():
                if rule.endpoint == "static":
                    continue
                url = str(rule)
                if not url.startswith(f"/{normalized}"):
                    continue
                methods = sorted(rule.methods - {"HEAD", "OPTIONS"})
                output.append({
                    "endpoint": rule.endpoint,
                    "url": url,
                    "methods": methods,
                })
            return jsonify(sorted(output, key=lambda x: x["url"])), 200


def _add_prefix_inspector(app, endpoint_name=None):
    """
    /prefixes → unique top-level route segments.
    """
    endpoint_name = endpoint_name or "prefix_inspector"
    if endpoint_name in app.view_functions:
        return

    @app.route("/prefixes", endpoint=endpoint_name, methods=["GET"])
    def prefix_list():
        prefixes = set()
        for rule in app.url_map.iter_rules():
            if rule.endpoint == "static":
                continue
            url = str(rule).lstrip("/")
            if url:
                prefixes.add("/" + url.split("/")[0])
        return jsonify(sorted(prefixes)), 200


# ──────────────────────────────────────────────────────────
# CORS wiring
# ──────────────────────────────────────────────────────────

def _apply_cors(app, *, allowed_origins=None, supports_credentials=None):
    """Apply CORS to the app.  No-op when no origins are specified."""
    cors_kwargs = {}

    if allowed_origins is not None:
        cors_kwargs["origins"] = make_list(allowed_origins)
    if supports_credentials is not None:
        cors_kwargs["supports_credentials"] = supports_credentials

    if cors_kwargs:
        CORS(app, **cors_kwargs)
    else:
        # Permissive default — explicit about it being wide open
        CORS(app)


# ──────────────────────────────────────────────────────────
# App factory
# ──────────────────────────────────────────────────────────

def get_Flask_app(*,
                  name=None,
                  routes=None,
                  bp_list=None,
                  url_prefix=None,
                  url_prefix_endpoint_name=None,
                  allowed_origins=None,
                  supports_credentials=None,
                  **flask_kwargs):
    """
    Minimal call:
        get_Flask_app(routes=routes)

    Full call:
        get_Flask_app(
            name="my_api",
            routes=routes,
            url_prefix="v1",
            allowed_origins=["https://example.com"],
            supports_credentials=True,
        )
    """
    # --- name: fall back to caller's __name__ ---
    if name is None:
        name = inspect.stack()[1].frame.f_globals.get("__name__", "abstract_flask")

    # --- blueprints: discover from routes module when bp_list not given ---
    if routes is not None and bp_list is None:
        bp_list = _discover_blueprints(routes, url_prefix)

    app = Flask(name, **flask_kwargs)

    _apply_cors(app, allowed_origins=allowed_origins,
                supports_credentials=supports_credentials)
    _attach_audit_log(app, name=name)
    _register_blueprints(app, bp_list)
    _add_endpoint_inspector(app, prefix=url_prefix)
    _add_prefix_inspector(app, endpoint_name=url_prefix_endpoint_name)

    return app


# ──────────────────────────────────────────────────────────
# Runner
# ──────────────────────────────────────────────────────────

def main_flask_start(app, key_head="", env_path=None):
    key_head = key_head.upper()
    schema = {
        "DEBUG": {"type": bool, "default": True},
        "HOST":  {"type": str,  "default": "0.0.0.0"},
        "PORT":  {"type": int,  "default": 5000},
    }
    resolved = {}
    for key, spec in schema.items():
        env_key = f"{key_head}_{key}" if key_head else key
        raw = get_env_value(path=env_path, key=env_key)
        resolved[key] = spec["type"](raw) if raw else spec["default"]

    app.run(
        debug=resolved["DEBUG"],
        host=resolved["HOST"],
        port=resolved["PORT"],
    )
