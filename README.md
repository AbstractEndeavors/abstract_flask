# abstract_flask

The staged bundle provides `ops.sh ACTION [--plan]` and `scripts/*.sh` for local Python installs and PyPI/GitHub push paths. Its Python source and `pyproject.toml` are at this directory's root.

A composable toolkit for standing up Flask APIs without repeating yourself. Handles blueprint discovery, CORS, request parsing, endpoint introspection, and route generation — so the only code you write is the code that matters.

## Install

```bash
pip install abstract_flask
```

## Quickstart

```python
# my_api/__init__.py
from . import routes
from abstract_flask import get_Flask_app

app = get_Flask_app(routes=routes, allowed_origins=["https://yourdomain.com"])
```

That's it. Blueprints are discovered from any `*_bp` objects in your `routes` module, CORS is applied, and introspection endpoints are registered automatically.

### Full signature

```python
app = get_Flask_app(
    name="my_api",              # Flask app name (default: caller's __name__)
    routes=routes,              # module to scan for *_bp Blueprints
    bp_list=None,               # or pass blueprints explicitly
    url_prefix="v1",            # prefix for blueprint registration + filtered /endpoints
    allowed_origins=["https://example.com"],
    supports_credentials=True,
)
```

### Running

```python
from abstract_flask import main_flask_start

main_flask_start(app, key_head="MYAPI", env_path=".env")
# reads MYAPI_DEBUG, MYAPI_HOST, MYAPI_PORT from env
```

## Package structure

```
abstract_flask/
├── abstract_flask.py        # App factory, CORS, audit logging, introspection
├── request_utils/
│   ├── request_utils.py     # get_request_data, extract_request_data
│   ├── get_requests.py      # required_keys, execute_request, get_spec_kwargs
│   └── parse_utils.py       # parse_request, parse_and_spec_vars
├── network_utils/
│   └── ip_utils.py          # get_host_ip, get_user_ip, get_ip_addr
├── user_utils/
│   └── user_utils.py        # get_user_name (from request or fallback)
└── generator/
    ├── generateFlaskRoute.py # Auto-generate Flask routes from Python files
    └── help_utils.py         # ?help introspection for any endpoint
```

## Core modules

### App factory (`abstract_flask.py`)

| Function | Purpose |
|---|---|
| `get_Flask_app(...)` | One-call app factory: blueprints, CORS, logging, introspection |
| `get_bp(name, abs_path)` | Create a named Blueprint with a logger |
| `main_flask_start(app)` | Run the app using env-driven host/port/debug |

Every app gets these endpoints for free:

- `GET /endpoints` — all registered routes
- `GET /<prefix>/endpoints` — routes under that prefix
- `GET /prefixes` — unique top-level route segments

### Request utilities (`request_utils/`)

```python
from abstract_flask.request_utils import get_request_data, required_keys, parse_request
```

- **`get_request_data(req)`** — Returns a dict from JSON body, form data, or query string (checked in that order).
- **`extract_request_data(req, res_type)`** — Full extraction: user, IP, headers, cookies, files, metadata. Pass `res_type` to narrow scope.
- **`required_keys(keys, req, defaults)`** — Validate that required keys are present; returns the data dict or a 400 error payload.
- **`parse_request(req)`** — Split a request into positional `args` and `kwargs`.
- **`get_spec_kwargs(var_types, args, **kwargs)`** — Type-coerced argument extraction against a schema.

### Route generator (`generator/`)

Auto-generate Flask endpoints from plain Python files:

```python
from abstract_flask.generator import generate_from_files

source = generate_from_files(
    directory="./my_functions",
    bp_name="auto_bp",
    url_prefix="generated",
)
```

Every public function becomes a `GET/POST` endpoint. Async functions are preserved. Pass `?help` to any generated endpoint to get parameter introspection via `offer_help`.

Register routes programmatically against an existing blueprint:

```python
from abstract_flask.generator import register_category

register_category(bp, "math", {
    "add": lambda a, b: a + b,
    "multiply": lambda a, b: a * b,
})
# creates /math/add, /math/multiply
```

### Network utilities (`network_utils/`)

```python
from abstract_flask.network_utils import get_host_ip, get_user_ip
```

### User utilities (`user_utils/`)

```python
from abstract_flask.user_utils import get_user_name
```

Resolves username from the request's `.user` attribute, falling back to IP-based lookup via `UserIPManager`.

## Dependencies

- `flask`, `flask_cors`, `werkzeug`
- `abstract_utilities`, `abstract_security`, `abstract_queries`

## License

MIT

## Author

[putkoff](https://github.com/AbstractEndeavors) — partners@abstractendeavors.com
## Declarative Flask route schema

`get_Flask_app` accepts a nested route dictionary directly. Callable leaves keep
its original GET/POST and `{ "result": ... }` response convention. A route spec
leaf can describe exact Flask behavior:

```python
from abstract_flask import get_Flask_app

routes = {"fleet": {"worker": {
    "view": worker_detail,
    "rule": "/fleet/workers/<worker_id>",
    "methods": ["GET"],
    "inputs": "path",       # or "merged" for query/form/JSON plus URL variables
    "response": "native", # or "result" for the original response wrapper
}}}
app = get_Flask_app(name="fleet", routes=routes, dual_prefix="/api")
```

A spec may use `rules` for several URL aliases and `endpoint` to name the
Flask endpoint. `strict_slashes` defaults to `False`; set it to `True` when
migrating an exact existing URL contract. Native responses preserve Flask
responses, status tuples, streaming responses, and ordinary dictionaries.
URL variables take precedence over submitted fields in `merged` input mode.

An arm entry point in `arms_group` may export a route dictionary as well as a
Blueprint. The factory creates and mounts its Blueprint automatically.
