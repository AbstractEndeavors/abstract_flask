---
# Abstract Flask

[![PyPI version](https://img.shields.io/pypi/v/abstract_flask.svg)](https://pypi.org/project/abstract_flask/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Versions](https://img.shields.io/pypi/pyversions/abstract_flask.svg)](https://pypi.org/project/abstract_flask/)

Utilities for building **Flask apps faster**: structured request parsing, safe argument extraction, user/IP introspection, logging helpers, and light-weight file/directory utilities — all packaged as small, composable modules.

**Version:** `0.0.0.23`  
**Status:** Alpha  
**License:** MIT  
**Author:** putkoff · partners@abstractendeavors.com  
**Repository:** [github.com/AbstractEndeavors/abstract_flask](https://github.com/AbstractEndeavors/abstract_flask)

---

## Why Abstract Flask?

Most Flask projects re-implement the same glue: normalize request data (query/form/JSON), validate keys, coerce types, find the caller’s user or IP, wire in basic logging, and juggle upload/download/process folders.  

**Abstract Flask** provides these as **small, composable utilities** you can import as needed — without forcing a project layout or framework.

---

## ✨ Features

- **Robust request parsing**
  - Unified access to JSON, form, and query data.
  - Required key validation and case-insensitive matching.
  - Convert positional args into typed kwargs with defaults.

- **Execution helpers**
  - Run a function with validated request data and return consistent `{result|error, status_code}` envelopes.

- **User/IP introspection**
  - Get authenticated user or resolve user by IP.
  - Extract complete request metadata (`headers`, `cookies`, `files`, etc.).

- **Blueprint & app tooling**
  - App factory with built-in request logging.
  - `/api/endpoints` route for quick endpoint discovery.

- **File & directory helpers**
  - Manage uploads, downloads, conversions, and user-specific directories with singleton managers.
  - Validate file extensions and safely move/copy files.

- **Network helpers**
  - Discover host IP with safe fallback to `127.0.0.1`.

---

## 📦 Installation

```bash
pip install abstract_flask
````

### Dependencies

**Core requirements:**

* `flask`
* `flask_cors`
* `werkzeug`
* `abstract_utilities`
* `abstract_pandas`

**Optional integrations:**

* `abstract_queries` — for user/IP resolution.
* `abstract_security` — for environment-driven config (`main_flask_start`).

---

## 🚀 Quickstart

```python
from abstract_flask.abstract_flask import get_Flask_app, get_bp
from abstract_flask.request_utils.request_utils import extract_request_data
from flask import jsonify

# 1) Create a Blueprint
bp, _logger = get_bp(name="example")

@bp.route("/hello", methods=["GET", "POST"])
def hello():
    data = extract_request_data(request)
    return jsonify({"message": "hi", "data": data}), 200

# 2) Create the app and register Blueprints
app = get_Flask_app(name="demo_app", bp_list=[bp])

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
```

---

## 📚 Core Modules

### Request utilities (`abstract_flask.request_utils`)

* `extract_request_data(req, res_type='all')`
* `get_request_info(req, res_type='user'|'ip_addr')`
* `get_request_data(req)`
* `required_keys(keys, req, defaults=None)`
* `get_only_kwargs(varList, *args, **kwargs)`
* `get_proper_kwargs(strings, **kwargs)`
* `get_spec_kwargs(var_types, args=None, **kwargs)`
* `execute_request(keys, req, func, desired_keys=None, defaults=None)`

### App helpers (`abstract_flask.abstract_flask`)

* `get_bp(name, abs_path=None)` → `(Blueprint, logger)`
* `addHandler(app, name=None)` → app with audit logging
* `get_Flask_app(name, bp_list=None, **kwargs)` → ready-to-run Flask app
* `jsonify_it(obj)` → `(jsonify(obj), status_code)`
* `/api/endpoints` → discover routes

### File utilities (`abstract_flask.file_utils`)

* `fileManager` (singleton, allowed extensions)
* `AbsManager` & `AbsManagerDynamic` (directory management)
* Helpers for uploads, downloads, conversions, per-user dirs.

### Network utilities (`abstract_flask.network_utils`)

* Safe host IP detection with fallback.

---

## 🧪 Examples

### Validate keys & execute a function

```python
from abstract_flask.request_utils.get_requests import execute_request

def add(a: int, b: int) -> int:
    return a + b

@app.route("/add", methods=["GET", "POST"])
def add_endpoint():
    result = execute_request(
        keys=["a", "b"],
        req=request,
        func=add,
        desired_keys=["a", "b"],
        defaults={"a": 0, "b": 0}
    )
    return jsonify(result), result.get("status_code", 200)
```

### Typed arg shaping with defaults

```python
from abstract_flask.request_utils.get_requests import get_spec_kwargs

spec = {
  "query": {"value": "",   "type": str},
  "limit": {"value": 25,   "type": int},
  "exact": {"value": False,"type": bool},
}

@app.route("/search", methods=["POST"])
def search():
    data = request.get_json(silent=True) or {}
    shaped = get_spec_kwargs(spec, [], **data)
    return jsonify(shaped)
```

---

## ⚠️ Known Quirks

* `main_flask_start` has typos (`iteems`, `KEY_VALUS`, default `PORT=True`). Fix before production.
* Docstring of `get_Flask_app` says “Quart” but it’s Flask.
* `get_request_data` is defined twice in `request_utils.py`; use the second implementation.
* Optional features rely on `abstract_queries` and `abstract_security`.

---

## 🔧 Compatibility

* **Python:** ≥ 3.6 (tested up to 3.11)
* **Flask:** Any modern 2.x release

---

## 🤝 Contributing

Contributions welcome!

1. Fork the repo.
2. Create a branch (`feat/your-feature`).
3. Add tests/examples.
4. Open a pull request.

Issues and PRs are tracked on GitHub: [AbstractEndeavors/abstract\_flask](https://github.com/AbstractEndeavors/abstract_flask).

---

## 📄 License

MIT © Abstract Endeavors / putkoff



---
