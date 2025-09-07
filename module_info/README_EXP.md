---

# Abstract Flask

Utilities for building Flask apps faster: structured request parsing, safe argument extraction, user/IP introspection, logging helpers, and light-weight file/directory utilities — all packaged as small, composable modules.

**Version:** `0.0.0.23`
**Status:** Alpha
**License:** MIT
**Author:** putkoff · [partners@abstractendeavors.com](mailto:partners@abstractendeavors.com)
**Repo:** [https://github.com/AbstractEndeavors/abstract\_flask](https://github.com/AbstractEndeavors/abstract_flask)

---

## Table of contents

* [Why Abstract Flask?](#why-abstract-flask)
* [Features](#features)
* [Install](#install)
* [Quickstart](#quickstart)
* [Core modules & APIs](#core-modules--apis)

  * [Request utilities (`abstract_flask.request_utils`)](#request-utilities-abstract_flaskrequest_utils)
  * [App helpers (`abstract_flask.abstract_flask`)](#app-helpers-abstract_flaskabstract_flask)
  * [File & directory helpers (`abstract_flask.file_utils`)](#file--directory-helpers-abstract_flaskfile_utils)
  * [Network helpers (`abstract_flask.network_utils`)](#network-helpers-abstract_flasknetwork_utils)
* [Directory layout](#directory-layout)
* [Examples](#examples)
* [Known quirks & notes](#known-quirks--notes)
* [Compatibility](#compatibility)
* [Contributing](#contributing)
* [License](#license)

---

## Why Abstract Flask?

Most Flask projects re-implement the same glue: normalize request data (query/form/JSON), validate keys, coerce types, find the caller’s user or IP, wire in basic logging, and juggle upload/download/process folders. **Abstract Flask** provides these bits as small functions and singletons you can drop into any app — without forcing a framework or project layout.

---

## Features

* **Robust request parsing**

  * One place to read JSON, form data, or query params (in that order).
  * Extract only the keys you want, with case-insensitive matching.
  * Validate required keys with clean error objects.
  * Coerce positional args to typed kwargs with defaults.
* **Execution helpers**

  * `execute_request(...)` combines validation, selection of desired keys, and function execution with consistent `{result|error, status_code}` envelopes.
* **User/IP introspection**

  * Pull the authenticated user (if present), or resolve a user from `remote_addr` via an IP manager.
  * Access structured request metadata in a single dict (`extract_request_data`).
* **Blueprint & app tooling**

  * Factory to build a Flask app with request logging wired in.
  * `/api/endpoints` route for quick endpoint discovery in dev.
* **File/directory helpers**

  * Common “uploads → process → downloads → converts → saved” flows, including per-user subfolders.
  * Singleton file manager for allowed extensions.
* **Network helpers**

  * Safe local IP detection with sensible fallbacks.
* **Zero lock-in**

  * Import only what you need; everything is plain Python + Flask.

---

## Install

```bash
pip install abstract_flask
```

> **Runtime dependencies (from `setup.py`):**
>
> * `flask`
> * `flask_cors`
> * `werkzeug`
> * `abstract_utilities`
> * `abstract_pandas`
>
> **Also referenced in code (optional/integrations):**
>
> * `abstract_queries` (for `UserManager` / `UserIPManager`)
> * `abstract_security` (for env lookups)

If you use the user/IP features, you’ll want `abstract_queries`. If you use environment-based server settings in `main_flask_start`, you’ll want `abstract_security`.

---

## Quickstart

Create an app, wire logging, and expose a test route:

```python
from abstract_flask.abstract_flask import get_Flask_app, get_bp
from abstract_flask.request_utils.request_utils import extract_request_data
from flask import jsonify

# 1) Create a Blueprint
bp, _logger = get_bp(name="example")

@bp.route("/hello", methods=["GET", "POST"])
def hello():
    data = extract_request_data()  # read user/ip/query/form/json/files/cookies/headers
    return jsonify({"message": "hi", "data": data}), 200

# 2) Create the app and register Blueprints
app = get_Flask_app(name="demo_app", bp_list=[bp])

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
```

---

## Core modules & APIs

### Request utilities (`abstract_flask.request_utils`)

These functions appear across `request_utils.py`, `parse_utils.py`, and `get_requests.py`. Import from the package path you prefer; the functionality is consistent.

**High-level extraction**

* `extract_request_data(req=None, res_type='all', user_manager=None, ip_manager=None) -> dict | None`
  Collects user, `ip_addr`, `query`, `form`, `json`, `files` (filename/type/size), `headers`, `cookies`, plus `method`, `url`, `path`, `host` when `res_type='all'`. If `req` is omitted inside a view, Flask’s proxy is used implicitly by your call site.

* `get_request_info(req=None, obj=None, res_type='user', ip_manager=None) -> str | None`
  Returns `'user'` (username) or `'ip_addr'`. Uses `req.user` if present; otherwise can resolve by `remote_addr` via an `UserIPManager`.

**Request data accessors**

* `get_request_data(req)`
  Returns a **dict** using the following precedence:

  1. JSON body (even if content type is wrong, parsed safely),
  2. `form` data,
  3. query string.
     If none found, `{}`.

* `parse_request(flask_request) -> (args, kwargs)`
  From JSON POST: `{"args": [...], **kwargs}`;
  otherwise: `?args=a&args=b&x=1` → `(["a","b"], {"x": "1"})`.

* `parse_and_return_json(flask_request) -> {"args": [...], "kwargs": {...}}`

* `parse_and_spec_vars(flask_request, varList) -> dict`
  Only keep keys listed in `varList`. If `varList` is a dict, its keys are used.

**Key/arg shapers**

* `required_keys(keys, req, defaults=None) -> dict | {"error":..., "status_code":400}`
  Ensure `keys` exist (from `get_request_data`). Returns the data dict or an error envelope.

* `get_only_kwargs(varList, *args, **kwargs) -> dict`
  Map positional `args` into `kwargs` by index using `varList`, then keep only listed keys.

* `get_proper_kwargs(strings, **kwargs) -> Any | None`
  Case-insensitive **exact** match first, then **partial** match of any key that contains the string; returns the **first matched value**, or `None`.

* `get_spec_kwargs(var_types, args=None, **kwargs) -> dict`
  Coerce inputs to typed kwargs with defaults.
  `var_types` is `{ key: {"value": default, "type": Type} }`.
  Positional `args` are consumed in order if the key isn’t in `kwargs`.

* `try_type(obj, typ) -> (value, success: bool)` and `process_args(args, typ) -> (remaining_args, value, success)`

**One-shot execution**

* `execute_request(keys, req, func, desired_keys=None, defaults=None) -> {"result":..., "status_code":200} | {"error":..., "status_code":...}`

  1. Validate `keys`,
  2. Build `desired_key_values` via `abstract_utilities.json_utils.get_desired_key_values`,
  3. Call `func(**desired_key_values)`, returning a consistent envelope.

**Utilities**

* `makeParams(*args, **kwargs)` / `async_makeParams(...)`
  Ensure positional args become a list, append non-None kwargs as a dict.

* `dump_if_json(obj)`
  If `dict`/`list`, attempt `json.dumps`.

* `get_args_jwargs_user_req(req, var_types={}) -> (data, args, username)`
  Use `extract_request_data` + `get_spec_kwargs` to return typed inputs and username.

---

### App helpers (`abstract_flask.abstract_flask`)

* `get_bp(name=None, abs_path=None, **bp_kwargs) -> (Blueprint, logger)`
  Creates a blueprint with name `<name>_bp`. If `name` is a file path, it’s normalized to a module-like name. Returns the `Blueprint` and a file logger bound to that name.

* `addHandler(app: Flask, *, name: str | None = None) -> Flask`
  Adds a file audit logger (`<name>.log`) with a custom `RequestFormatter` that includes `remote_addr` and resolved `user`.
  Also registers:

  * `@app.before_request` hook that logs a user’s IP when authenticated.
  * `/api/endpoints` (GET/POST) returning a sorted list of `(route, methods)` for quick discovery.
    Idempotent via an `_endpoints_registered` flag.

* `register_bps(app, bp_list) -> app`
  Registers an iterable of blueprints.

* `get_Flask_app(name, bp_list=None, **kwargs) -> Flask`
  Small app factory using `addHandler` and `register_bps`.

  > Note: docstring mentions “Quart”, but the implementation is Flask.

* `jsonify_it(obj)`
  If `obj` is a dict and contains `status_code`, returns `(jsonify(obj), status_code)` for one-line view returns.

* `main_flask_start(app, key_head='', env_path=None, **kwargs)`
  Intended to read `DEBUG/HOST/PORT` from env (prefixed by `key_head`) via `abstract_security.get_env_value` and call `app.run(...)`. See **Known quirks** for a couple of small typos here.

---

### File & directory helpers (`abstract_flask.file_utils`)

> There are two styles in the tree — older single-file helpers and a newer, more modular folder (`src/abstract_flask/file_utils/`). Functionality centers on:

* **Singletons**

  * `fileManager`: singleton with `allowed_extensions` (defaults include `ods,csv,xls,xlsx,xlsb`).
  * `AbsManager` / `AbsManagerDynamic`: singletons that create and manage base folders and **per-user** folders for:

    * `uploads/`, `process/`, `downloads/`, `converts/`, `saved/`, `data/`, `users/`
  * Helpers to ensure/create dirs, move/copy between them, generate UUID-style names, validate extensions, save/read files, and cleanup.

* **Directory functions**

  * Get full paths for user-specific subfolders, move to `process` / `downloads`, copy to `saved`, convert files (thin wrapper), and validate file/storage objects (e.g., check `werkzeug.FileStorage`).

These are intentionally small utilities — not an opinionated storage system — so you can combine them with your own storage backend or persistence layer.

---

### Network helpers (`abstract_flask.network_utils`)

* **IP utilities**
  Determine the host IP by opening a UDP socket to a well-known address with timeout and falling back to `127.0.0.1` on failure. Useful for binding or advertising a reachable IP in local/dev setups.

---

## Directory layout

Your repository appears to be mid-migration from a flat module to a more modular package. The current source structure:

```
src/abstract_flask/
├── abstract_flask.py                  # app factory, blueprints, logging, /api/endpoints
├── file_utils/
│   ├── file_utils.py                  # modernized file utils surface
│   ├── imports.py
│   └── request_files.py
├── network_utils/
│   ├── imports.py
│   └── ip_utils.py
├── request_utils/
│   ├── call_tracking.py               # (placeholder)
│   ├── get_requests.py                # required_keys, execute_request, typed arg shaping
│   ├── imports.py                     # pulls from abstract_utilities & abstract_queries
│   ├── parse_utils.py                 # parse_(...) helpers for args/kwargs, spec vars
│   └── request_utils.py               # extract_request_data, get_request_info, etc.
└── user_utils/
    ├── imports.py
    └── user_utils.py
```

Legacy descriptors under `module_info/` summarize older single-file helpers (e.g., `Abs_Manager.py`, `directories.py`, `file_utils.py`, `network_tools.py`).

---

## Examples

### 1) Validate keys, execute a function, return a consistent envelope

```python
from abstract_flask.request_utils.get_requests import execute_request

def add(a: int, b: int) -> int:
    return a + b

# POST JSON: {"a": 2, "b": 5}
# GET: /add?a=2&b=5
@app.route("/add", methods=["GET", "POST"])
def add_endpoint():
    result = execute_request(
        keys=["a", "b"],          # required
        req=request,
        func=add,
        desired_keys=["a", "b"],  # subset passed to func
        defaults={"a": 0, "b": 0}
    )
    # result looks like {"result": 7, "status_code": 200} or {"error": "...", "status_code": 400/500}
    return jsonify(result), result.get("status_code", 200)
```

### 2) Typed argument shaping with defaults

```python
from abstract_flask.request_utils.get_requests import get_spec_kwargs

# POST JSON: {"limit": "50"}  -> coerce to int
spec = {
  "query": {"value": "",   "type": str},
  "limit": {"value": 25,   "type": int},
  "exact": {"value": False,"type": bool},
}

@app.route("/search", methods=["GET","POST"])
def search():
    data = request.get_json(silent=True) or {}
    args = []
    shaped = get_spec_kwargs(spec, args, **data)
    # shaped: {"query": "", "limit": 50, "exact": False}
    return jsonify(shaped)
```

### 3) Case-insensitive key matching (exact then partial)

```python
from abstract_flask.request_utils.get_requests import get_proper_kwargs

value = get_proper_kwargs(["user_id", "userid"], **{"UserID": 42})
assert value == 42
```

### 4) Per-user file paths and moves (pattern)

```python
# Conceptually (exact names depend on the concrete file_utils surface you use):
mgr = AbsManagerDynamic()   # singleton
user_upload = mgr.user_uploads_dir("alice")
saved_path  = mgr.copy_to_saved("alice", "/tmp/myfile.csv")
dl_path     = mgr.move_to_downloads("alice", saved_path)
```

### 5) Discover endpoints during development

```
GET /api/endpoints
[
  ["/hello", "GET, POST"],
  ["/add", "GET, POST"],
  ...
]
```

---

## Known quirks & notes

> These are small cleanup items you may want to address if you’re contributing.

* **Typo in `main_flask_start`**

  * Uses `KEY_VALUS` (`VALUS`) and `iteems()` (should be `items()`), and `PORT` default is `True` (should be an `int`). Consider:

  ```python
  KEY_VALUES = {
      "DEBUG": {"type": bool, "default": True},
      "HOST":  {"type": str,  "default": "0.0.0.0"},
      "PORT":  {"type": int,  "default": 5000},
  }
  for key, spec in KEY_VALUES.items():
      env_key = f"{key_head.upper()}_{key}"
      typ     = spec["type"]
      default = spec["default"]
      KEY_VALUES[key] = typ(get_env_value(path=env_path, key=env_key) or default)
  app.run(debug=KEY_VALUES["DEBUG"], host=KEY_VALUES["HOST"], port=KEY_VALUES["PORT"])
  ```

* **Docstring mismatch**

  * `get_Flask_app` says “Quart app factory” but it’s a Flask app factory.

* **Duplicate `get_request_data` definition**

  * In `request_utils.request_utils.py` there’s an early `get_request_data(req)` and then an improved one later that returns JSON→form→query in that order. Keep the **second** implementation.

* **Optional dependencies**

  * User/IP resolution uses `abstract_queries` (`UserManager`, `UserIPManager`). If you don’t install it, those features should be guarded or mocked.

* **Legacy vs modular structure**

  * The `module_info/` synopses refer to older single-file utilities (`Abs_Manager.py`, etc.). The live `src/` uses a modular tree (`file_utils/`, `request_utils/`, `network_utils/`). Functionality overlaps; prefer the code in `src/`.

---

## Compatibility

* **Python:** `>=3.6` (package metadata)
  Developed against **Python 3.11** (classifiers).
* **Flask:** Any modern 2.x release should work.

---

## Contributing

PRs and issues are welcome!

1. Fork the repo.
2. Create a feature branch: `feat/your-thing`.
3. Add tests or example routes when possible.
4. Open a pull request with a clear description.

If you’re tackling items in **Known quirks & notes**, reference this README so reviewers have context.

---

## License

MIT © Abstract Endeavors / putkoff

---

### Appendix: API cheat-sheet

* `abstract_flask.request_utils`

  * `extract_request_data(req=None, res_type='all', user_manager=None, ip_manager=None)`
  * `get_request_info(req=None, obj=None, res_type='user', ip_manager=None)`
  * `get_request_data(req)`
  * `parse_request(req)` / `parse_and_return_json(req)` / `parse_and_spec_vars(req, varList)`
  * `required_keys(keys, req, defaults=None)`
  * `get_only_kwargs(varList, *args, **kwargs)`
  * `get_proper_kwargs(strings, **kwargs)`
  * `get_spec_kwargs(var_types, args=None, **kwargs)`
  * `try_type(obj, typ)` / `process_args(args, typ)`
  * `execute_request(keys, req, func, desired_keys=None, defaults=None)`
  * `makeParams(*args, **kwargs)` / `async_makeParams(...)`
  * `dump_if_json(obj)`
  * `get_args_jwargs_user_req(req, var_types={})`

* `abstract_flask.abstract_flask`

  * `get_bp(name=None, abs_path=None, **bp_kwargs)`
  * `addHandler(app, name=None)`
  * `register_bps(app, bp_list)`
  * `get_Flask_app(name, bp_list=None, **kwargs)`
  * `jsonify_it(obj)`
  * `main_flask_start(app, key_head='', env_path=None, **kwargs)`

* `abstract_flask.file_utils`

  * `fileManager` (singleton, allowed extensions)
  * `AbsManager` / `AbsManagerDynamic` (singleton directory managers)
  * Helpers for per-user directories and file moves/copies/conversions.

* `abstract_flask.network_utils`

  * IP discovery helpers with graceful fallback.

---
