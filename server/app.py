"""
Vi-Sdet-Selector API

Two endpoints, two very different guarantees:

- POST /predict          → deterministic rule engine (server/rules.py).
                            No API key needed, no hallucination risk, always
                            returns the same output for the same input.

- POST /predict/explain   → same rule engine, plus a natural-language
                            explanation written by an LLM (server/reasoning.py).
                            Needs ANTHROPIC_API_KEY. This is the part that's
                            covered by the DeepEval faithfulness/relevancy
                            tests in tests/test_deepeval_reasoning.py.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from server.rules import ElementAttributes, PredictionResponse, predict_strategy
from server.reasoning import generate_natural_reasoning

app = FastAPI(
    title="Vi-Sdet-Selector API",
    description="AI-assisted selector strategy advisor for Playwright tests.",
    version="0.2.0",
)


class ExplainedPredictionResponse(PredictionResponse):
    explanation: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse)
def predict(element: ElementAttributes):
    return predict_strategy(element)


@app.post("/predict/explain", response_model=ExplainedPredictionResponse)
def predict_with_explanation(element: ElementAttributes):
    prediction = predict_strategy(element)
    try:
        explanation = generate_natural_reasoning(
            signals=prediction.reasoning,
            recommended_strategy=prediction.recommended_strategy,
            alternative=prediction.alternative,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return ExplainedPredictionResponse(
        **prediction.model_dump(),
        explanation=explanation,
    )
