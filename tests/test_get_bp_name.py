"""get_bp applies the _bp marker idempotently (no doubling)."""
from abstract_flask import get_bp
from abstract_flask.abstract_flask import bp_name_for


def test_bp_name_for_idempotent():
    assert bp_name_for("settings") == "settings_bp"
    assert bp_name_for("math_bp") == "math_bp"      # already suffixed -> unchanged
    assert bp_name_for("review_bp") == "review_bp"
    assert bp_name_for(None) == "flask_bp"


def test_get_bp_names():
    bp, _ = get_bp("settings", __name__)
    assert bp.name == "settings_bp"
    bp2, _ = get_bp("math_bp", __name__)
    assert bp2.name == "math_bp"                    # not math_bp_bp
