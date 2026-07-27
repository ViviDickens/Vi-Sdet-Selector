"""
This is the actual "AI Quality" test in the project.

The rule engine (test_rules.py) is deterministic — no need for DeepEval
there, plain asserts are enough. What DeepEval checks is the ONE part
of this system that's genuinely generative: the natural-language
explanation written by an LLM in server/reasoning.py.

Two things get measured:
- Faithfulness: does the explanation avoid claiming anything that isn't
  in the rule signals it was given?
- Answer Relevancy: does the explanation actually answer "why this
  strategy?" instead of drifting off topic?

Requires ANTHROPIC_API_KEY (to generate the explanation) and
OPENAI_API_KEY (DeepEval's default judge model). Skips cleanly if
either is missing — this suite is opt-in, not required to run the API.
"""

import os

import pytest

from server.rules import ElementAttributes, predict_strategy
from server.reasoning import generate_natural_reasoning

pytestmark = pytest.mark.skipif(
    not (os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("OPENAI_API_KEY")),
    reason=(
        "Needs ANTHROPIC_API_KEY (generates the explanation) and "
        "OPENAI_API_KEY (DeepEval's default judge model) to run."
    ),
)


SAMPLE_ELEMENT = ElementAttributes(
    tag="button",
    classes=["css-1a2b3c"],
    data_testid="submit-btn",
    aria_label="Submit form",
    xpath="//div[2]/button[3]",
    text="Submit",
)


def test_explanation_is_faithful_and_relevant():
    from deepeval import assert_test
    from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
    from deepeval.test_case import LLMTestCase

    prediction = predict_strategy(SAMPLE_ELEMENT)
    explanation = generate_natural_reasoning(
        signals=prediction.reasoning,
        recommended_strategy=prediction.recommended_strategy,
        alternative=prediction.alternative,
    )

    # The explanation must actually name the strategy it's defending.
    # Faithfulness can't catch this on its own: "xpath likely brittle" is a
    # legitimate signal, so an explanation that wrongly recommended XPath
    # wouldn't contradict the context.
    assert prediction.recommended_strategy in explanation.lower()

    # retrieval_context has to mirror everything the generator was given,
    # not just the signals — _build_prompt also hands it the recommended
    # strategy and the alternative. Leaving those out makes the explanation
    # look like it's asserting unsupported facts when it isn't.
    retrieval_context = [
        *prediction.reasoning,
        f"recommended strategy: {prediction.recommended_strategy}",
        f"alternative strategy: {prediction.alternative or 'none'}",
    ]

    test_case = LLMTestCase(
        input=(
            f"Why is '{prediction.recommended_strategy}' the recommended "
            "locator strategy for this element?"
        ),
        actual_output=explanation,
        retrieval_context=retrieval_context,
    )

    faithfulness = FaithfulnessMetric(threshold=0.7)
    relevancy = AnswerRelevancyMetric(threshold=0.7)

    assert_test(test_case, [faithfulness, relevancy])
