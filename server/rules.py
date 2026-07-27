"""
Deterministic rule engine for locator strategy selection.

This is the core of Vi-Sdet-Selector: no ML model, no black box. Every
recommendation comes from an explicit, readable rule, and `reasoning`
is literally the list of rules that fired — nothing hidden, nothing to
defend that you can't explain line by line.

Priority order: data-testid > aria-label > static css id > xpath (fallback).
"""

import re
from typing import List, Optional

from pydantic import BaseModel, Field

# ── Dynamic-class / brittle-xpath detection ──────────────────────────

_DYNAMIC_CLASS_PATTERNS = [
    re.compile(r"^css-[a-z0-9]+$", re.IGNORECASE),       # emotion / styled-components
    re.compile(r"^sc-[a-zA-Z0-9]+$"),                     # styled-components
    re.compile(r"^jsx-\d+$"),                             # styled-jsx
    re.compile(r"^_[a-zA-Z0-9]+_[a-z0-9]{5,}$"),          # CSS modules (e.g. _button_1a2b3)
    # Generic hash suffix. The suffix must contain at least one digit —
    # without that guard, any word built only from the letters a-f reads as
    # a hash ("btn-added", "user-facade", "nav-decade" all matched before).
    # An all-letter hex hash is rare, and the css-/sc-/jsx- patterns above
    # already cover the common generators that emit them.
    re.compile(r"^[a-zA-Z]+-(?=[a-f0-9]*\d)[a-f0-9]{5,}$", re.IGNORECASE),
]


def is_dynamic_class(class_name: str) -> bool:
    return any(p.match(class_name) for p in _DYNAMIC_CLASS_PATTERNS)


def is_xpath_brittle(xpath: str) -> bool:
    if not xpath:
        return False
    has_positional_index = re.search(r"\[\d+\]", xpath) is not None
    has_stable_anchor = "@id" in xpath or "id(" in xpath
    return has_positional_index and not has_stable_anchor


# ── Request / response models ────────────────────────────────────────

class ElementAttributes(BaseModel):
    tag: str = Field(..., description="HTML tag name, e.g. 'button'")
    id: Optional[str] = None
    classes: List[str] = Field(default_factory=list)
    data_testid: Optional[str] = None
    aria_label: Optional[str] = None
    xpath: Optional[str] = None
    text: Optional[str] = None


class PredictionResponse(BaseModel):
    recommended_strategy: str
    confidence: float
    reasoning: List[str]
    alternative: Optional[str] = None


# ── Prediction logic ──────────────────────────────────────────────────

def predict_strategy(el: ElementAttributes) -> PredictionResponse:
    reasoning: List[str] = []
    dynamic_classes = [c for c in el.classes if is_dynamic_class(c)]
    xpath_brittle = is_xpath_brittle(el.xpath) if el.xpath else False

    # 1. data-testid is the gold standard when present
    if el.data_testid:
        reasoning.append("element has stable test id")
        if dynamic_classes:
            reasoning.append("dynamic class detected")
        if xpath_brittle:
            reasoning.append("xpath likely brittle")
        alternative = "aria-label" if el.aria_label else ("id" if el.id else "css")
        return PredictionResponse(
            recommended_strategy="data-testid",
            confidence=0.94,
            reasoning=reasoning,
            alternative=alternative,
        )

    # 2. aria-label — stable and accessibility-relevant
    if el.aria_label:
        reasoning.append("no data-testid present")
        reasoning.append("aria-label is stable and accessibility-relevant")
        if dynamic_classes:
            reasoning.append("dynamic class detected")
        alternative = "id" if el.id and not is_dynamic_class(el.id) else "css"
        return PredictionResponse(
            recommended_strategy="aria-label",
            confidence=0.85,
            reasoning=reasoning,
            alternative=alternative,
        )

    # 3. static id via CSS selector
    if el.id and not is_dynamic_class(el.id):
        reasoning.append("no data-testid or aria-label present")
        reasoning.append("static id detected")
        if dynamic_classes:
            reasoning.append("only dynamic classes present besides id")
        return PredictionResponse(
            recommended_strategy="css",
            confidence=0.75,
            reasoning=reasoning,
            alternative="xpath" if el.xpath else "text",
        )

    # 4. fallback — nothing stable to anchor on
    reasoning.append("no data-testid, aria-label, or static id present")
    if dynamic_classes:
        reasoning.append("only dynamic classes detected")
    if xpath_brittle:
        reasoning.append("xpath likely brittle")
        confidence = 0.40
    else:
        confidence = 0.55

    # Only offer css as the alternative when there's actually something
    # stable to anchor it on — a static class. Otherwise css would resolve
    # to a bare tag selector, which matches every element of that tag.
    static_classes = [c for c in el.classes if not is_dynamic_class(c)]
    if static_classes:
        alternative = "css"
    elif el.text:
        alternative = "text"
    else:
        alternative = None

    return PredictionResponse(
        recommended_strategy="xpath",
        confidence=confidence,
        reasoning=reasoning,
        alternative=alternative,
    )
