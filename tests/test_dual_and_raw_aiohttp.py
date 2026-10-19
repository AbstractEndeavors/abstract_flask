"""mount_dual_blueprints dual-mounts bare + /api; aiohttp register_categories
accepts raw `async def h(request)` handlers (request/app passthrough) as well as
pure functions.
"""
from __future__ import annotations

import asyncio

import pytest


def test_mount_dual_blueprints():
    flask = pytest.importorskip("flask")
    from abstract_flask import register_categories, mount_dual_blueprints

    inner = flask.Blueprint("inner_bp", __name__)
    register_categories(inner, {"llm/x": {"ping": lambda: "pong"}})
    core, core_api = mount_dual_blueprints([inner], name="core")

    app = flask.Flask(__name__)
    app.register_blueprint(core)
    app.register_blueprint(core_api)
    rules = {str(r) for r in app.url_map.iter_rules()}
    assert "/llm/x/ping" in rules            # bare tree
    assert "/api/llm/x/ping" in rules         # /api tree
    c = app.test_client()
    assert c.get("/llm/x/ping").get_json() == {"result": "pong"}
    assert c.post("/api/llm/x/ping").get_json() == {"result": "pong"}


def test_aiohttp_raw_handler_and_pure():
    pytest.importorskip("aiohttp")
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer
    from abstract_flask import register_categories

    async def whoami(request):                 # raw aiohttp handler using app state
        return web.json_response({"db": request.app["DB"], "q": dict(request.query)})

    def add(a, b):                             # pure function
        return int(a) + int(b)

    app = web.Application()
    app["DB"] = "pg://x"
    register_categories(app, {"fleet": {"whoami": whoami}, "math": {"add": add}})

    async def drive():
        c = TestClient(TestServer(app))
        await c.start_server()
        try:
            r = await c.get("/fleet/whoami", params={"n": "1"})
            assert (await r.json()) == {"db": "pg://x", "q": {"n": "1"}}
            r = await c.post("/math/add", json={"a": 2, "b": 5})
            assert (await r.json()) == {"result": 7}
        finally:
            await c.close()

    asyncio.run(drive())
