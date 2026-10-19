import inspect
import logging
import os
import re
import sys

from flask import Blueprint, Flask, jsonify, request, has_request_context
from flask_cors import CORS
from werkzeug.utils import secure_filename

from .imports import make_list, get_logFile, eatAll,get_env_value

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


def bp_name_for(name):
    """The blueprint/logger name for ``name``, carrying the ``_bp`` convention.

    The suffix marks blueprint objects and their per-blueprint log files so they
    are easy to identify and grep. It is applied **idempotently**: a name that
    already ends in ``_bp`` is left alone, so ``get_bp("math_bp")`` yields
    ``math_bp`` (not the old doubled ``math_bp_bp``) while ``get_bp("settings")``
    still yields ``settings_bp``.
    """
    base = "flask" if name in (None, "") else str(name)
    return base if base.endswith("_bp") else f"{base}_bp"


def get_bp(name=None, abs_path=None, **bp_kwargs):
    name, abs_path = get_name(name=name, abs_path=abs_path)
    bp_name = bp_name_for(name)
    bp_logger = get_logFile(bp_name)
    bp_logger.info(f"Python path: {sys.path!r}")
    bp = Blueprint(bp_name, abs_path, **bp_kwargs)
    return bp, bp_logger


def load_entrypoint_blueprints(group):
    """Every Blueprint published to an entry-point ``group`` (each guarded).

    Lets optional packages plug a blueprint into an app by declaring it in an
    entry-point group (e.g. ``hugpy.arms``); a broken/absent one only logs."""
    out = []
    try:
        from importlib.metadata import entry_points
    except Exception:  # noqa: BLE001
        return out
    for ep in entry_points(group=group):
        try:
            bp = ep.load()
            if isinstance(bp, Blueprint):
                out.append(bp)
            elif isinstance(bp, dict):
                from .generator.generateFlaskRoute import register_categories
                name = re.sub(r"[^A-Za-z0-9_]", "_", ep.name)
                schema_bp, _ = get_bp(name, ep.module)
                register_categories(schema_bp, bp)
                out.append(schema_bp)
            else:
                logger.warning("entry point %r is %s, not a Blueprint or route schema",
                               ep.name, type(bp).__name__)
        except Exception as exc:  # noqa: BLE001
            logger.warning("entry point %r (%s) not loaded: %r", ep.name, ep.value, exc)
    return out


def mount_dual_blueprints(blueprints, *, name="core", prefix="/api",
                          arms_group=None, import_name=None):
    """Collapse the "mount every subpackage blueprint on a bare tree AND under a
    prefix" pattern into one call. Returns ``(bare_bp, prefixed_bp)``:

        core_bp, core_api_bp = mount_dual_blueprints(
            [web_bp, brain_bp, ...], name="core", arms_group="hugpy.arms")

    Each blueprint in ``blueprints`` (plus any Blueprint published to the
    ``arms_group`` entry-point group, if given) is registered on BOTH parents, so
    the whole surface is served bare (``/llm/...``) and under ``prefix``
    (``/api/llm/...``). Expose the two returned blueprints at a routes module's top
    level and ``get_Flask_app(routes=...)`` discovers and registers them."""
    import_name = import_name or __name__
    bare = Blueprint(name, import_name)
    prefixed = Blueprint(f"{name}_api", import_name, url_prefix=prefix)
    bps = list(blueprints or [])
    if arms_group:
        bps += load_entrypoint_blueprints(arms_group)
    for bp in bps:
        bare.register_blueprint(bp)
        prefixed.register_blueprint(bp)
    return bare, prefixed


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
                  dual_prefix=None,
                  arms_group=None,
                  allowed_origins=None,
                  supports_credentials=None,
                  debug=None,
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

    ``routes`` may be a module whose top-level ``*_bp`` Blueprints are discovered,
    or a nested route dictionary. A dictionary is registered on one blueprint.

    ``dual_prefix`` (e.g. ``"/api"``) additionally mounts every discovered (and
    arm) blueprint a SECOND time under that prefix, so the whole surface is served
    bare AND under the prefix without a hand-rolled aggregator.
    ``arms_group`` (e.g. ``"hugpy.arms"``) also mounts every Blueprint published to
    that entry-point group (each guarded), on both trees when ``dual_prefix`` is set.
    """
    # --- name: fall back to caller's __name__ ---
    if name is None:
        name = inspect.stack()[1].frame.f_globals.get("__name__", "abstract_flask")

    # --- blueprints: discover from routes module when bp_list not given ---
    if routes is not None and bp_list is None:
        if isinstance(routes, dict):
            from .generator.generateFlaskRoute import register_categories
            schema_bp, _ = get_bp(name, name)
            register_categories(schema_bp, routes)
            bp_list = [(schema_bp, f"/{url_prefix}/")] if url_prefix else [schema_bp]
        else:
            bp_list = _discover_blueprints(routes, url_prefix)

    app = Flask(name, **flask_kwargs)
    if debug is not None:
        app.debug = debug
    _apply_cors(app, allowed_origins=allowed_origins,
                supports_credentials=supports_credentials)
    _attach_audit_log(app, name=name)
    _register_blueprints(app, bp_list)

    def _mount_second(bp):
        app.register_blueprint(bp, url_prefix=dual_prefix, name=f"{bp.name}_api")

    if dual_prefix:
        for entry in (bp_list or []):
            _mount_second(entry[0] if isinstance(entry, tuple) else entry)
    if arms_group:
        for bp in load_entrypoint_blueprints(arms_group):
            app.register_blueprint(bp)
            if dual_prefix:
                _mount_second(bp)

    _add_endpoint_inspector(app, prefix=url_prefix or (dual_prefix.strip("/") if dual_prefix else None))
    _add_prefix_inspector(app, endpoint_name=url_prefix_endpoint_name)
    # Browser observability supplies X-Hugpy-Trace-Id per request.  Requests
    # without that header remain completely uninstrumented.
    from .execution_trace import install_execution_trace
    install_execution_trace(app)

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
