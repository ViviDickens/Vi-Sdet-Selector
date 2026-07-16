"""
Optional natural-language explanation layer.

The rule engine (rules.py) already produces a `reasoning` list that's
100% deterministic and requires no API key. This module is a separate,
opt-in layer: it takes that same signal list and asks an LLM (Claude)
to turn it into a short paragraph a human can read.

This is the part that's actually "AI" here — and because it's an LLM
writing free text, it's also the part that can hallucinate. That's
exactly what the DeepEval test suite (tests/test_deepeval_reasoning.py)
checks: that the generated paragraph doesn't claim anything beyond the
signals it was given.

Requires ANTHROPIC_API_KEY. The base /predict endpoint does NOT need
this module at all — it only backs /predict/explain.
"""

import os
from typing import List, Optional


def _build_prompt(signals: List[str], recommended_strategy: str, alternative: Optional[str]) -> str:
    signal_text = "\n".join(f"- {s}" for s in signals)
    return (
        "You are a QA automation expert explaining a Playwright locator strategy "
        "recommendation to a fellow engineer. Base your explanation ONLY on the "
        "signals listed below. Do not invent DOM details, tools, metrics, or facts "
        "that are not present in the signals.\n\n"
        f"Recommended strategy: {recommended_strategy}\n"
        f"Alternative strategy: {alternative or 'none'}\n"
        f"Signals detected:\n{signal_text}\n\n"
        "Write a 2-3 sentence explanation in plain English."
    )


def generate_natural_reasoning(
    signals: List[str],
    recommended_strategy: str,
    alternative: Optional[str] = None,
    model: str = "claude-3-5-haiku-20241022",
) -> str:
    """
    Turns the deterministic rule signals into a natural-language explanation.

    Raises RuntimeError with a clear message if ANTHROPIC_API_KEY is missing,
    instead of failing with an opaque SDK error deep in a stack trace.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. /predict/explain needs it to generate "
            "natural-language reasoning. The plain /predict endpoint works fine "
            "without it — this layer is optional."
        )

    import anthropic  # imported lazily so the core API works without the SDK installed

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=200,
        messages=[
            {"role": "user", "content": _build_prompt(signals, recommended_strategy, alternative)}
        ],
    )
    return message.content[0].text.strip()
