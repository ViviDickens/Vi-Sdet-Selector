"""
Unit tests for the deterministic rule engine. No API key needed — these
run in CI on every push and prove the priority order works:
data-testid > aria-label > static css id > xpath (fallback).
"""

import pytest

from server.rules import ElementAttributes, is_dynamic_class, predict_strategy


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


# ── Dynamic-class detection ──────────────────────────────────────────

@pytest.mark.parametrize(
    "class_name",
    [
        "css-1a2b3c",      # emotion
        "sc-bdVaJa9",      # styled-components
        "jsx-123456",      # styled-jsx
        "_button_1a2b3",   # css modules
        "header-beef1",    # generic hash suffix (has a digit)
    ],
)
def test_dynamic_classes_are_detected(class_name):
    assert is_dynamic_class(class_name)


@pytest.mark.parametrize(
    "class_name",
    [
        "submit-button",
        "email-field",
        # Words built only from the letters a-f used to read as hex hashes.
        "btn-added",
        "user-facade",
        "nav-decade",
    ],
)
def test_hand_written_classes_are_not_mistaken_for_hashes(class_name):
    assert not is_dynamic_class(class_name)


def test_static_id_survives_a_hex_looking_word_suffix():
    """A regression guard: id='btn-added' used to be read as a dynamic
    hash, which downgraded the recommendation from css to xpath."""
    result = predict_strategy(ElementAttributes(tag="button", id="btn-added"))

    assert result.recommended_strategy == "css"
    assert "static id detected" in result.reasoning


# ── Fallback alternative ─────────────────────────────────────────────

def test_fallback_offers_css_only_when_a_static_class_exists():
    result = predict_strategy(
        ElementAttributes(tag="div", classes=["css-9f8e7d", "card-body"])
    )

    assert result.recommended_strategy == "xpath"
    assert result.alternative == "css"


def test_fallback_offers_text_when_nothing_but_text_is_available():
    result = predict_strategy(
        ElementAttributes(tag="div", classes=["css-9f8e7d"], text="Add to cart")
    )

    assert result.alternative == "text"


def test_fallback_offers_no_alternative_when_there_is_nothing_to_anchor_on():
    result = predict_strategy(ElementAttributes(tag="div", classes=["css-9f8e7d"]))

    assert result.alternative is None
