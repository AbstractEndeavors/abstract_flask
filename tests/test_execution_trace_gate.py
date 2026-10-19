"""execution_trace is gated: process opt-in + both headers, rate-limited, one
POST per traced request from one sender thread, and it never fights another
tracer.

    PYTHONPATH=live/src python -m pytest -q live/tests/test_execution_trace_gate.py
"""
from __future__ import annotations

import importlib
import sys
import threading
import time

import pytest
from flask import Flask, jsonify

H = {"X-Hugpy-Trace": "1", "X-Hugpy-Trace-Id": "t-1"}


@pytest.fixture
def et(monkeypatch):
    for k in ("ABSTRACT_FLASK_EXECUTION_TRACE", "ABSTRACT_FLASK_TRACE_RATE", "ABSTRACT_FLASK_TRACE_QUEUE",
              "ABSTRACT_FLASK_TRACE_MODULES"):
        monkeypatch.delenv(k, raising=False)
    import abstract_flask.execution_trace as mod
    mod = importlib.reload(mod)
    posted = []
    monkeypatch.setattr(mod, "_post", lambda payload: posted.append(payload))
    mod.posted = posted
    return mod


def _helper(n):
    return n * 2


def make_app(et, console_trace=False):
    app = Flask(__name__)
    if console_trace:
        app.extensions["console_trace"] = True
    et.install_execution_trace(app)

    @app.get("/work")
    def work():
        return jsonify({"n": _helper(21)})

    @app.get("/boom")
    def boom():
        raise RuntimeError("nope")

    return app


def drain(et, n, timeout=5):
    end = time.time() + timeout
    while time.time() < end and len(et.posted) < n:
        time.sleep(0.01)


def test_off_without_process_opt_in(et):
    app = make_app(et)
    assert not app.before_request_funcs, "no hooks may be registered without the env opt-in"
    r = app.test_client().get("/work", headers=H)
    assert r.status_code == 200 and "X-Hugpy-Trace-Server" not in r.headers
    assert et._sender is None and et.posted == []


def test_trace_id_alone_does_not_trace(et, monkeypatch):
    monkeypatch.setenv("ABSTRACT_FLASK_EXECUTION_TRACE", "1")
    app = make_app(et)
    r = app.test_client().get("/work", headers={"X-Hugpy-Trace-Id": "only-id"})
    assert "X-Hugpy-Trace-Server" not in r.headers and et._sender is None


def test_one_post_per_traced_request_no_thread_per_call(et, monkeypatch):
    monkeypatch.setenv("ABSTRACT_FLASK_EXECUTION_TRACE", "1")
    monkeypatch.setenv("ABSTRACT_FLASK_TRACE_RATE", "0")
    app = make_app(et)
    c = app.test_client()
    before = threading.active_count()
    for i in range(5):
        r = c.get("/work", headers={**H, "X-Hugpy-Trace-Id": f"t-{i}"})
        assert r.headers["X-Hugpy-Trace-Server"] == "abstract_flask; traced"
    drain(et, 5)
    assert len(et.posted) == 5
    assert threading.active_count() <= before + 1, "only the single sender thread may be added"
    body = et.posted[0]["body"]
    fns = {e["function"] for e in body["events"]}
    assert {"work", "_helper"} <= fns
    assert all("site-packages" not in e["file"] for e in body["events"])
    assert et.posted[0]["kind"] == "flask_trace" and body["status"] == 200
    assert sys.getprofile() is None


def test_rate_limit(et, monkeypatch):
    monkeypatch.setenv("ABSTRACT_FLASK_EXECUTION_TRACE", "1")
    monkeypatch.setenv("ABSTRACT_FLASK_TRACE_RATE", "2")
    app = make_app(et)
    c = app.test_client()
    heads = [c.get("/work", headers={**H, "X-Hugpy-Trace-Id": f"r-{i}"}).headers.get("X-Hugpy-Trace-Server") for i in range(10)]
    traced = heads.count("abstract_flask; traced")
    assert 1 <= traced <= 3
    assert heads.count("abstract_flask; skipped=rate") == 10 - traced


def test_defers_to_console_trace_and_busy_profiler(et, monkeypatch):
    monkeypatch.setenv("ABSTRACT_FLASK_EXECUTION_TRACE", "1")
    monkeypatch.setenv("ABSTRACT_FLASK_TRACE_RATE", "0")
    r = make_app(et, console_trace=True).test_client().get("/work", headers=H)
    assert "X-Hugpy-Trace-Server" not in r.headers
    app = make_app(et)

    def other(frame, event, arg):
        return None
    sys.setprofile(other)
    try:
        r = app.test_client().get("/work", headers=H)
        assert sys.getprofile() is other
    finally:
        sys.setprofile(None)
    assert r.headers["X-Hugpy-Trace-Server"] == "abstract_flask; skipped=profiler-busy"


def test_error_is_recorded_once(et, monkeypatch):
    monkeypatch.setenv("ABSTRACT_FLASK_EXECUTION_TRACE", "1")
    monkeypatch.setenv("ABSTRACT_FLASK_TRACE_RATE", "0")
    app = make_app(et)
    assert app.test_client().get("/boom", headers=H).status_code == 500
    drain(et, 1)
    assert len(et.posted) == 1
    err = et.posted[0]["body"]["error"]
    assert err["type"] == "RuntimeError" and err["traceback"][-1]["function"] == "boom"


def test_full_queue_drops_and_counts(et, monkeypatch):
    monkeypatch.setenv("ABSTRACT_FLASK_EXECUTION_TRACE", "1")
    monkeypatch.setenv("ABSTRACT_FLASK_TRACE_RATE", "0")
    monkeypatch.setenv("ABSTRACT_FLASK_TRACE_QUEUE", "1")
    gate = threading.Event()
    monkeypatch.setattr(et, "_post", lambda payload: gate.wait(5))
    app = make_app(et)
    c = app.test_client()
    for i in range(6):
        c.get("/work", headers={**H, "X-Hugpy-Trace-Id": f"q-{i}"})
    gate.set()
    st = et.stats()
    assert st["dropped_queue_full"] >= 3
    assert st["queued"] + st["dropped_queue_full"] == 6
