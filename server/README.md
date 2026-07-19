# Server

FastAPI backend exposing the locator strategy advisor.

- **`rules.py`** — the actual engine. A deterministic, testable rule set
  (data-testid > aria-label > static css id > xpath fallback). No trained
  model, no black box.
- **`reasoning.py`** — optional layer that asks Claude to turn the rule
  engine's signals into a natural-language explanation. Requires
  `ANTHROPIC_API_KEY`.
- **`app.py`** — wires both into two endpoints:
  - `POST /predict` — deterministic, no API key needed.
  - `POST /predict/explain` — adds the natural-language explanation
    (503 if `ANTHROPIC_API_KEY` isn't set).

Run locally with `uvicorn server.app:app --reload` from the repo root.
