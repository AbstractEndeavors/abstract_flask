"""Opt-in request execution tracing for browser-driven Flask calls — GATED.

Nothing happens unless BOTH sides opt in:

* the PROCESS: ``ABSTRACT_FLASK_EXECUTION_TRACE=1`` when the app is built.
  Without it ``install_execution_trace`` registers no hooks at all (zero cost);
* the REQUEST: ``X-Hugpy-Trace: 1`` *and* ``X-Hugpy-Trace-Id: <id>``.  An id
  alone (e.g. a browser that tags every request) never starts tracing.

Bounded on every axis:

* rate: ``ABSTRACT_FLASK_TRACE_RATE`` traced requests per second per process
  (token bucket, default 2; ``0`` = unlimited).  Over the limit a request runs
  untraced and the response says ``X-Hugpy-Trace-Server: abstract_flask; skipped=rate``;
* events: ``HUGPY_TRACE_MAX_EVENTS`` per request (default 3000), application
  frames only (``ABSTRACT_FLASK_TRACE_MODULES`` = module-name globs narrows it);
* emission: ONE POST per traced request, after the response, by ONE sender
  thread fed from a bounded queue (``ABSTRACT_FLASK_TRACE_QUEUE``, default 100).
  A full queue drops the batch and counts it (``stats()``); a request never
  waits on the sink.  (Before 2026-10-01 every Python call spawned a thread and
  a POST.)

It never fights another tracer: an app that already installed hugpy's
``console_trace`` (``app.extensions["console_trace"]``) is left to it, and a
request that starts while another profiler is active is not traced.

Sink: ``HUGPY_STATION_URL`` (default ``http://127.0.0.1:7006``) +
``/api/provenance/ingest``, kind ``flask_trace``.
"""
from __future__ import annotations

import fnmatch
import json
import os
import queue
import sys
import threading
import time
import traceback
import urllib.request

from flask import g, request

ENV_ENABLE = "ABSTRACT_FLASK_EXECUTION_TRACE"
_LIB_MARKERS = ("/site-packages/", "/dist-packages/", "/lib/python")
_THIS = os.path.abspath(__file__)
_tls = threading.local()


def _truthy(v):
    return str(v or "").strip().lower() in ("1", "true", "on", "yes")


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def enabled():
    return _truthy(os.environ.get(ENV_ENABLE))


# ── sender: one thread, bounded queue, one POST per traced request ─────────
class _Sender:
    def __init__(self):
        self.pid = os.getpid()
        self.q = queue.Queue(maxsize=max(1, _env_int("ABSTRACT_FLASK_TRACE_QUEUE", 100)))
        self.stats = {"queued": 0, "sent": 0, "dropped_queue_full": 0, "send_errors": 0}
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._run, name="abstract-flask-trace-sender", daemon=True)
        self.thread.start()

    def put(self, payload):
        try:
            self.q.put_nowait(payload)
            with self.lock:
                self.stats["queued"] += 1
            return True
        except queue.Full:
            with self.lock:
                self.stats["dropped_queue_full"] += 1
            return False

    def _run(self):
        while True:
            payload = self.q.get()
            try:
                _post(payload)
                with self.lock:
                    self.stats["sent"] += 1
            except Exception:  # noqa: BLE001 — the sink is best-effort, counted
                with self.lock:
                    self.stats["send_errors"] += 1
            finally:
                self.q.task_done()


_sender = None
_sender_lock = threading.Lock()


def _get_sender():
    global _sender
    s = _sender
    if s is None or s.pid != os.getpid():
        with _sender_lock:
            s = _sender
            if s is None or s.pid != os.getpid():
                _sender = s = _Sender()
    return s


def stats():
    s = _sender
    if s is None:
        return {"queued": 0, "sent": 0, "dropped_queue_full": 0, "send_errors": 0}
    with s.lock:
        return dict(s.stats)


def _post(payload):
    base = (os.environ.get("HUGPY_STATION_URL") or "http://127.0.0.1:7006").rstrip("/")
    data = json.dumps(payload, default=str).encode()
    req = urllib.request.Request(base + "/api/provenance/ingest", data=data,
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=2).read()


# ── rate limit ────────────────────────────────────────────────────────────
class _Bucket:
    def __init__(self):
        self.lock = threading.Lock()
        self.tokens = None
        self.last = time.monotonic()

    def allow(self):
        rate = _env_int("ABSTRACT_FLASK_TRACE_RATE", 2)
        if rate <= 0:
            return True
        with self.lock:
            now = time.monotonic()
            if self.tokens is None:
                self.tokens = float(rate)
            self.tokens = min(float(rate), self.tokens + (now - self.last) * rate)
            self.last = now
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False


_bucket = _Bucket()


# ── the per-request profiler ──────────────────────────────────────────────
def _wanted(frame, modules):
    filename = frame.f_code.co_filename
    if any(m in filename for m in _LIB_MARKERS) or os.path.abspath(filename) == _THIS:
        return False
    if modules:
        mod = frame.f_globals.get("__name__", "")
        return any(fnmatch.fnmatchcase(mod, m) for m in modules)
    return True


def _profile(frame, event, arg):
    st = getattr(_tls, "state", None)
    if st is None or event not in ("call", "return") or not _wanted(frame, st["modules"]):
        return
    if len(st["events"]) >= st["max"]:
        st["truncated"] += 1
        return
    code = frame.f_code
    ev = {"phase": event, "function": code.co_name, "module": frame.f_globals.get("__name__", ""),
          "file": code.co_filename, "line": frame.f_lineno, "t": time.perf_counter() - st["t0"]}
    st["events"].append(ev)


def install_execution_trace(app):
    """Install request-scoped tracing — only when the process opted in."""
    if getattr(app, "_hugpy_execution_trace", False):
        return app
    if not enabled():
        return app
    app._hugpy_execution_trace = True

    @app.before_request
    def _hugpy_trace_begin():
        if app.extensions.get("console_trace"):
            return None          # hugpy central's console_trace owns tracing there
        if request.headers.get("X-Hugpy-Trace") != "1":
            return None
        trace_id = request.headers.get("X-Hugpy-Trace-Id", "").strip()[:160]
        if not trace_id:
            return None
        if sys.getprofile() is not None:
            g._hugpy_trace_skip = "profiler-busy"
            return None
        if not _bucket.allow():
            g._hugpy_trace_skip = "rate"
            return None
        modules = [m.strip() for m in (os.environ.get("ABSTRACT_FLASK_TRACE_MODULES") or "").split(",") if m.strip()]
        _tls.state = {"id": trace_id, "t0": time.perf_counter(), "started": time.time(), "events": [],
                      "max": max(1, _env_int("HUGPY_TRACE_MAX_EVENTS", 3000)), "truncated": 0, "modules": modules,
                      "error": None, "status": None}
        g._hugpy_trace_active = True
        sys.setprofile(_profile)
        return None

    @app.after_request
    def _hugpy_trace_end(response):
        if getattr(g, "_hugpy_trace_active", False):
            st = getattr(_tls, "state", None)
            if st is not None:
                st["status"] = response.status_code
            response.headers["X-Hugpy-Trace-Server"] = "abstract_flask; traced"
        elif getattr(g, "_hugpy_trace_skip", None):
            response.headers["X-Hugpy-Trace-Server"] = f"abstract_flask; skipped={g._hugpy_trace_skip}"
        return response

    @app.teardown_request
    def _hugpy_trace_teardown(error):
        if not getattr(g, "_hugpy_trace_active", False):
            return
        g._hugpy_trace_active = False
        if sys.getprofile() is _profile:
            sys.setprofile(None)
        st = getattr(_tls, "state", None)
        _tls.state = None
        if st is None:
            return
        if error is not None:
            st["error"] = {"type": type(error).__name__, "message": str(error)[:2000],
                           "traceback": [{"function": f.name, "file": f.filename, "line": f.lineno}
                                         for f in traceback.extract_tb(error.__traceback__)][-40:]}
        body = {"trace_id": st["id"], "method": request.method, "path": request.path,
                "endpoint": request.endpoint or "", "status": st["status"] if st["status"] is not None else (500 if error else None),
                "duration_ms": round((time.perf_counter() - st["t0"]) * 1000, 3), "started": st["started"],
                "events": st["events"], "truncated": st["truncated"], "error": st["error"]}
        _get_sender().put({"kind": "flask_trace", "body": body, "source": "flask-execution-trace",
                           "actor": "flask", "operation": "request", "trace_id": st["id"]})

    return app
