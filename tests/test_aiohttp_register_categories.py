"""register_categories(target, ALL_CATEGORIES) works identically on an aiohttp
app and a Flask blueprint.

    PYTHONPATH=src python -m pytest -q tests/test_aiohttp_register_categories.py
"""
from __future__ import annotations

import asyncio

import pytest


def _add(a, b):
    """add two numbers"""
    return int(a) + int(b)


async def _greet(name):
    return f"hi {name}"


ALL_CATEGORIES = {
    "math": {"add": _add},
    "hello": {"greet": _greet},
}


# ── aiohttp path ────────────────────────────────────────────────────────────

def test_aiohttp_routes_registered_and_behave():
    pytest.importorskip("aiohttp")
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer
    from abstract_flask import register_categories

    app = web.Application()
    register_categories(app, ALL_CATEGORIES)

    # both the plain and trailing-slash rules exist for GET+POST
    seen = {(r.method, r.resource.canonical) for r in app.router.routes()}
    for path in ("/math/add", "/math/add/", "/hello/greet", "/hello/greet/"):
        assert ("GET", path) in seen, f"missing GET {path}"
        assert ("POST", path) in seen, f"missing POST {path}"

    async def drive():
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            # sync fn, JSON body
            r = await client.post("/math/add", json={"a": 2, "b": 3})
            assert (await r.json()) == {"result": 5}
            # async fn, query string, trailing slash
            r = await client.get("/hello/greet/", params={"name": "sam"})
            assert (await r.json()) == {"result": "hi sam"}
            # help
            r = await client.post("/math/add", json={"help": True})
            body = await r.json()
            assert body["_add"]["doc"] == "add two numbers"
            # error surfaces as 500 {"error": ...}
            r = await client.post("/math/add", json={"a": "x", "b": 3})
            assert r.status == 500 and "error" in (await r.json())
        finally:
            await client.close()

    asyncio.run(drive())


# ── Flask path unchanged (regression) ───────────────────────────────────────

def test_flask_path_unchanged():
    flask = pytest.importorskip("flask")
    from abstract_flask import get_bp, register_categories

    bp, _ = get_bp("sample_bp", __name__)
    register_categories(bp, {"math": {"add": _add}})

    app = flask.Flask(__name__)
    app.register_blueprint(bp)
    c = app.test_client()
    assert c.post("/math/add", json={"a": 2, "b": 3}).get_json() == {"result": 5}
    assert c.get("/math/add/", query_string={"a": 4, "b": 1}).get_json() == {"result": 5}
