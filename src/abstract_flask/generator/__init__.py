from .generateFlaskRoute import *
from .help_utils import *
from .categories import *
try:  # aiohttp support is optional — present only when aiohttp is installed
    from .aiohttp_routes import (
        get_aiohttp_app,
        register_route_aiohttp,
        register_category_aiohttp,
        register_categories_aiohttp,
    )
except Exception:  # noqa: BLE001 — Flask-only installs need no aiohttp
    pass
