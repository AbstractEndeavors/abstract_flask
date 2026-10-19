"""register_categories accepts nested category trees (dict nesting encodes the
path) and a callable at the top level becomes a single-segment route. A nested
tree and the equivalent flat 2-level form register identical routes.
"""
from __future__ import annotations

import asyncio

import pytest


def _add(a=0, b=0):
    return int(a) + int(b)


def test_nested_equals_flat_flask():
    flask = pytest.importorskip("flask")
    from abstract_flask import get_bp, register_categories

    nested = {"llm": {"central": {"pulls": {"pull_start": _add}}}, "v1": {"models": _add}, "arms": _add}
    flat = {"llm/central/pulls": {"pull_start": _add}, "v1": {"models": _add}, "arms": _add}

    def rules_for(tree):
        bp, _ = get_bp("t_bp", __name__)
        register_categories(bp, tree)
        app = flask.Flask(__name__)
        app.register_blueprint(bp)
        return {str(r) for r in app.url_map.iter_rules() if r.endpoint != "static"}

    rn, rf = rules_for(nested), rules_for(flat)
    assert rn == rf
    assert "/llm/central/pulls/pull_start" in rn
    assert "/v1/models" in rn
    assert "/arms" in rn           # single-segment (callable at top level)


def test_nested_aiohttp():
    pytest.importorskip("aiohttp")
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer
    from abstract_flask import register_categories

    app = web.Application()
    register_categories(app, {"llm": {"central": {"pulls": {"pull_start": _add}}}, "arms": _add})

    async def drive():
        c = TestClient(TestServer(app))
        await c.start_server()
        try:
            r = await c.post("/llm/central/pulls/pull_start", json={"a": 2, "b": 3})
            assert (await r.json()) == {"result": 5}
            r = await c.post("/arms", json={"a": 1, "b": 1})
            assert (await r.json()) == {"result": 2}
        finally:
            await c.close()

    asyncio.run(drive())
