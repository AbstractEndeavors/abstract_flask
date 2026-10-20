"""The nested category tree is the one route convention: ``<param>`` keys are
path parameters that reach plain handlers, a spec leaf declares exact methods
and a bare response on the same tree path (no absolute rule needed), a list of
specs puts several method-specific views on one URL, and sections' trees merge
into one describable catalog.
"""
from __future__ import annotations

import pytest
from flask import Flask

from abstract_flask import (
    describe_categories, get_bp, merge_categories, register_categories, category_paths, spec,
)


def _app(tree):
    bp, _ = get_bp("tree_bp", __name__)
    register_categories(bp, tree)
    app = Flask(__name__)
    app.register_blueprint(bp)
    return app


def test_param_key_feeds_plain_callable_and_url_identity_wins():
    def run_get(run_id, verbose=False):
        return {"run_id": run_id, "verbose": bool(verbose)}

    app = _app({"llm": {"benchmark": {"runs": {"": lambda: ["r1"], "<run_id>": run_get}}}})
    c = app.test_client()
    assert c.get("/llm/benchmark/runs").get_json() == {"result": ["r1"]}
    assert c.get("/llm/benchmark/runs/abc").get_json() == {"result": {"run_id": "abc", "verbose": False}}
    assert c.post("/llm/benchmark/runs/abc", json={"run_id": "forged", "verbose": True}).get_json() == {
        "result": {"run_id": "abc", "verbose": True}}
    # endpoint names never carry the angle brackets or converters
    names = {r.endpoint for r in app.url_map.iter_rules()}
    assert "tree_bp.llm/benchmark/runs_run_id" in names
    assert not any("<" in n for n in names)


def test_spec_leaf_in_tree_derives_its_rule_from_nesting():
    def ticket_act(tid, action=None):
        return {"tid": tid, "action": action}, 202

    tree = {"llm": {"help": {"tickets": {
        "": {"view": lambda: {"tickets": []}, "methods": ["GET"], "response": "native"},
        "<int:tid>": {"act": {"view": ticket_act, "methods": ["POST"], "response": "native"}},
    }}}}
    app = _app(tree)
    c = app.test_client()
    assert c.get("/llm/help/tickets").get_json() == {"tickets": []}          # bare, no envelope
    assert c.post("/llm/help/tickets").status_code == 405
    r = c.post("/llm/help/tickets/7/act", json={"action": "approve"})
    assert r.status_code == 202 and r.get_json() == {"tid": 7, "action": "approve"}
    assert "tree_bp.llm_help_tickets_tid_act" in {r.endpoint for r in app.url_map.iter_rules()}


def test_spec_list_puts_several_methods_on_one_path():
    tree = {"llm": {"help": {"sessions": [
        {"view": lambda: {"sessions": ["s1"]}, "methods": ["GET"], "response": "native"},
        {"view": lambda model=None: ({"started": model}, 201), "methods": ["POST"], "response": "native"},
    ]}}}
    c = _app(tree).test_client()
    assert c.get("/llm/help/sessions").get_json() == {"sessions": ["s1"]}
    r = c.post("/llm/help/sessions", json={"model": "m"})
    assert r.status_code == 201 and r.get_json() == {"started": "m"}
    assert c.delete("/llm/help/sessions").status_code == 405
    names = {r.endpoint for r in _app(tree).url_map.iter_rules()}
    assert {"tree_bp.llm_help_sessions_get", "tree_bp.llm_help_sessions_post"} <= names
    with pytest.raises(TypeError):
        register_categories(get_bp("bad", __name__)[0], {"x": [lambda: 1]})


def test_merge_categories_composes_sections_and_rejects_conflicts():
    def a():
        return 1

    def b():
        return 2

    brain = {"llm": {"brain": {"": a}}}
    grading = {"llm": {"benchmark": {"runs": {"": b}}}, "v1": {"models": a}}
    merged = merge_categories(brain, grading)
    assert category_paths(merged) == ["/llm/benchmark/runs", "/llm/brain", "/v1/models"]
    assert brain == {"llm": {"brain": {"": a}}}            # inputs untouched
    merged["llm"]["extra"] = {}
    assert "extra" not in brain["llm"]
    with pytest.raises(ValueError):
        merge_categories(brain, {"llm": {"brain": {"": b}}})
    with pytest.raises(ValueError):
        merge_categories(brain, {"llm": {"brain": b}})       # node vs leaf
    assert merge_categories(brain, brain) == brain             # same object twice is fine


def test_describe_categories_is_a_json_catalog():
    def runs(limit=20):
        """Benchmark history."""
        return []

    tree = {"llm": {"benchmark": {"runs": {
        "": runs,
        "<run_id>": {"view": lambda run_id: {}, "methods": "GET", "response": "native"},
    }}}}
    rows = describe_categories(tree)
    assert [r["path"] for r in rows] == ["/llm/benchmark/runs", "/llm/benchmark/runs/<run_id>"]
    first, second = rows
    assert first["kind"] == "callable" and first["methods"] == ["GET", "POST"] and first["response"] == "result"
    assert first["doc"] == "Benchmark history." and first["params"] == [
        {"name": "limit", "default": 20, "required": False}]
    assert first["view"].endswith("runs") and ":" in first["view"]
    assert second["kind"] == "spec" and second["methods"] == ["GET"] and second["response"] == "native"
    assert second["params"] == [{"name": "run_id", "default": None, "required": True}]
    import json
    json.dumps(rows)   # JSON-able as promised


def test_spec_helper_is_the_explicit_dict():
    fn = lambda: {}
    assert spec(fn, "GET", response="native") == {"view": fn, "methods": ["GET"], "response": "native", "inputs": "merged"}
    assert spec(fn)["methods"] == ["GET", "POST"]
    assert spec(fn, ["put", "patch"], inputs="path", strict_slashes=True)["methods"] == ["PUT", "PATCH"]
    c = _app({"a": {"b": spec(lambda x=1: {"x": int(x)}, "GET", response="native")}}).test_client()
    assert c.get("/a/b?x=5").get_json() == {"x": 5} and c.post("/a/b").status_code == 405


def test_describe_defaults_are_json_safe():
    _UNSET = object()

    def update(group_id=None, name=_UNSET):
        return {}

    row = describe_categories({"g": {"update": update}})[0]
    assert row["params"][1]["default"].startswith("<object object")
    import json
    json.dumps(row)
