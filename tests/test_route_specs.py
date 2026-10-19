"""Exact route specs coexist with the original category callable contract."""

from flask import Flask, jsonify, request
import pytest

from abstract_flask import get_bp, register_categories


def test_spec_preserves_path_methods_status_and_native_response():
    bp, _ = get_bp("specs", __name__)

    def detail(item_id):
        return jsonify({"item": item_id}), 207

    def update(item_id):
        return {"item": item_id, "body": request.get_json()}

    register_categories(bp, {"items": {
        "detail": {"view": detail, "rule": "/items/<item_id>", "methods": ["GET"],
                   "inputs": "path", "response": "native"},
        "update": {"view": update, "rule": "/items/<item_id>", "methods": ["PATCH"],
                   "inputs": "path", "response": "native"},
        "legacy": lambda x=0: int(x) + 1,
    }})
    app = Flask(__name__)
    app.register_blueprint(bp)
    client = app.test_client()
    assert client.get("/items/abc").status_code == 207
    assert client.get("/items/abc").get_json() == {"item": "abc"}
    assert client.patch("/items/abc", json={"item_id": "forged"}).get_json() == {
        "item": "abc", "body": {"item_id": "forged"}}
    assert client.post("/items/abc").status_code == 405
    assert client.get("/items/legacy?x=2").get_json() == {"result": 3}


def test_spec_merges_request_fields_but_url_identity_wins():
    bp, _ = get_bp("merged", __name__)
    register_categories(bp, {"items": {"update": {
        "view": lambda item_id, count=0: {"item_id": item_id, "count": count},
        "rule": "/items/<item_id>", "methods": ["POST"],
        "response": "native"}}})
    app = Flask(__name__)
    app.register_blueprint(bp)
    assert app.test_client().post("/items/real", json={"item_id": "fake", "count": 2}).get_json() == {
        "item_id": "real", "count": 2}


def test_spec_multiple_rules_and_invalid_schema():
    bp, _ = get_bp("aliases", __name__)
    register_categories(bp, {"x": {"y": {"view": lambda: "ok", "rules": ["/one", "/two"],
                                        "inputs": "path", "response": "native", "methods": "GET"}}})
    app = Flask(__name__)
    app.register_blueprint(bp)
    assert app.test_client().get("/one").data == b"ok"
    assert app.test_client().get("/two").data == b"ok"
    with pytest.raises(ValueError):
        register_categories(get_bp("bad", __name__)[0], {"x": {"y": {
            "view": lambda: None, "response": "surprise"}}})


def test_app_factory_accepts_entire_route_dictionary():
    from abstract_flask import get_Flask_app
    app = get_Flask_app(name="schema_app", routes={"fleet": {"workers": {
        "view": lambda worker: {"worker": worker},
        "rule": "/fleet/workers/<worker>", "methods": ["GET"],
        "inputs": "path", "response": "native"}}}, dual_prefix="/api")
    client = app.test_client()
    assert client.get("/fleet/workers/w1").get_json() == {"worker": "w1"}
    assert client.get("/api/fleet/workers/w1").get_json() == {"worker": "w1"}
    assert client.post("/fleet/workers/w1").status_code == 405


def test_arm_entrypoint_can_export_route_dictionary(monkeypatch):
    from abstract_flask import get_Flask_app
    import importlib.metadata

    class Entry:
        name = "example-arm"
        module = __name__

        def load(self):
            return {"arm": {"health": {"view": lambda: {"ok": True},
                                       "methods": ["GET"], "response": "native"}}}

    monkeypatch.setattr(importlib.metadata, "entry_points", lambda **_: [Entry()])
    app = get_Flask_app(name="arms", routes={}, arms_group="test.arms")
    assert app.test_client().get("/arm/health").get_json() == {"ok": True}


def test_spec_can_supply_route_defaults_for_catch_all():
    bp, _ = get_bp("catch_all", __name__)
    register_categories(bp, {"proxy": {"view": lambda rest: rest or "root",
                                      "rules": [{"rule": "/proxy/", "defaults": {"rest": ""}},
                                                "/proxy/<path:rest>"],
                                      "methods": ["GET"], "inputs": "path", "response": "native"}})
    app = Flask(__name__)
    app.register_blueprint(bp)
    client = app.test_client()
    assert client.get("/proxy/").data == b"root"
    assert client.get("/proxy/a/b").data == b"a/b"
