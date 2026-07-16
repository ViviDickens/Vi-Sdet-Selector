"""
Unit tests for the deterministic rule engine. No API key needed — these
run in CI on every push and prove the priority order works:
data-testid > aria-label > static css id > xpath (fallback).
"""

from server.rules import ElementAttributes, predict_strategy


def test_data_testid_is_preferred_even_with_dynamic_class_and_brittle_xpath():
    el = ElementAttributes(
        tag="button",
        classes=["css-1a2b3c"],
        data_testid="submit-btn",
        aria_label="Submit form",
        xpath="//div[2]/button[3]",
    )
    result = predict_strategy(el)

    assert result.recommended_strategy == "data-testid"
    assert result.confidence == 0.94
    assert result.reasoning == [
        "element has stable test id",
        "dynamic class detected",
        "xpath likely brittle",
    ]
    assert result.alternative == "aria-label"


def test_falls_back_to_aria_label_without_testid():
    el = ElementAttributes(tag="button", aria_label="Close dialog")
    result = predict_strategy(el)

    assert result.recommended_strategy == "aria-label"
    assert "no data-testid present" in result.reasoning


def test_falls_back_to_css_with_static_id():
    el = ElementAttributes(tag="input", id="email-field")
    result = predict_strategy(el)

    assert result.recommended_strategy == "css"
    assert "static id detected" in result.reasoning


def test_dynamic_id_is_not_trusted_as_static():
    el = ElementAttributes(tag="input", id="css-4f5e6d")
    result = predict_strategy(el)

    assert result.recommended_strategy != "css"


def test_falls_back_to_xpath_when_nothing_stable():
    el = ElementAttributes(tag="div", classes=["css-9f8e7d"], xpath="//div[3]/span[2]")
    result = predict_strategy(el)

    assert result.recommended_strategy == "xpath"
    assert result.confidence == 0.40
    assert "xpath likely brittle" in result.reasoning


def test_low_confidence_fallback_without_brittle_xpath():
    el = ElementAttributes(tag="div", classes=["css-9f8e7d"])
    result = predict_strategy(el)

    assert result.recommended_strategy == "xpath"
    assert result.confidence == 0.55
