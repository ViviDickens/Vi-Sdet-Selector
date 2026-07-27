"""
Endpoint-level tests for server/app.py.

test_rules.py covers predict_strategy() directly; this file covers the
HTTP layer around it — serialization, validation, and the 503 that
/predict/explain returns when the optional AI layer isn't configured.
No API key needed: the explain path is exercised only in its unconfigured
state, which is exactly the branch that doesn't call out to anything.
"""

import pytest
from fastapi.testclient import TestClient

from server.app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict_returns_full_prediction_shape():
    response = client.post(
        "/predict",
        json={
            "tag": "button",
            "data_testid": "submit-btn",
            "aria_label": "Submit form",
            "classes": ["css-1a2b3c"],
            "xpath": "//div[2]/button[3]",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["recommended_strategy"] == "data-testid"
    assert body["confidence"] == 0.94
    assert body["alternative"] == "aria-label"
    assert "element has stable test id" in body["reasoning"]


def test_predict_accepts_a_minimal_element():
    response = client.post("/predict", json={"tag": "div"})

    assert response.status_code == 200
    assert response.json()["recommended_strategy"] == "xpath"


def test_predict_rejects_a_body_without_tag():
    response = client.post("/predict", json={})

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"tag": "button", "aria_label": "Close dialog"}, "aria-label"),
        ({"tag": "input", "id": "email-field"}, "css"),
        ({"tag": "div", "classes": ["css-9f8e7d"]}, "xpath"),
    ],
)
def test_predict_covers_each_priority_branch(payload, expected):
    response = client.post("/predict", json=payload)

    assert response.status_code == 200
    assert response.json()["recommended_strategy"] == expected


def test_explain_returns_503_without_an_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    response = client.post("/predict/explain", json={"tag": "button", "id": "go"})

    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]
