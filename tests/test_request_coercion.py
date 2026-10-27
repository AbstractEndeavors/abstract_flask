"""Request field coercion: numeric strings become numbers; typed JSON values keep
their type (a JSON true must not reach a handler as 1)."""
from flask import Flask, abort

from abstract_flask import get_bp, make_number, register_categories


def test_make_number_only_coerces_numeric_strings():
    assert make_number("3") == 3 and make_number("2.5") == 2.5 and make_number("x") == "x"
    assert make_number(True) is True and make_number(False) is False
    assert make_number(7) == 7 and make_number(None) is None and make_number([1]) == [1]


def test_nonfinite_fields_reach_handler_validation():
    for value in ("nan", "NaN", "inf", "-Infinity", "1e999"):
        assert make_number(value) == value
    assert make_number("1e3") == 1000.0
    assert make_number("-2.5e-2") == -0.025


def test_json_booleans_survive_the_merged_registrar():
    bp, _ = get_bp("coerce", __name__)
    register_categories(bp, {"t": {"echo": lambda grade=None, n=None: {"grade": grade, "n": n}}})
    app = Flask(__name__)
    app.register_blueprint(bp)
    c = app.test_client()
    assert c.post("/t/echo", json={"grade": True, "n": "4"}).get_json() == {"result": {"grade": True, "n": 4}}
    assert c.get("/t/echo?grade=true&n=4").get_json() == {"result": {"grade": "true", "n": 4}}


def test_handler_http_errors_keep_their_status_and_json_body():
    def reject():
        abort(403, description="denied by handler")
    bp, _ = get_bp("reject", __name__)
    register_categories(bp, {"t": {"reject": reject}})
    app = Flask(__name__)
    app.register_blueprint(bp)
    response = app.test_client().post("/t/reject")
    assert response.status_code == 403
    assert response.get_json() == {"error": "denied by handler"}
