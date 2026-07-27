# Vi-Sdet-Selector

Explainable locator strategy advisor for Playwright tests.

Given a DOM element's attributes, a **deterministic rule engine**
recommends the most resilient locator strategy — `data-testid`,
`aria-label`, CSS, or XPath — with every decision traceable to a named
rule. No trained model, no black box. An optional layer asks Claude to
turn those same rules into a plain-English explanation, validated with
**DeepEval** so it can't claim more than the rules actually found.

---

## Features

- **Rule-based scoring engine** (`server/rules.py`) — explicit, testable
  signals (stable test id, dynamic class, brittle xpath) drive every
  recommendation. Priority order: `data-testid` → `aria-label` → static
  CSS id → `xpath` (fallback).
- **`POST /predict`** — deterministic endpoint, zero API keys required.
- **`POST /predict/explain`** (opt-in) — same recommendation, plus a
  natural-language explanation written by Claude. Needs
  `ANTHROPIC_API_KEY`.
- **DeepEval test suite** — Faithfulness + Answer Relevancy checks on
  the AI-generated explanation, catching hallucination against the
  rule engine's own signals.
- **TypeScript SDK** (`playwright-sdk/`) — `predict.ts` turns a
  prediction into a locator string you can hand to `page.locator()`.
  Example test runs against [saucedemo.com](https://www.saucedemo.com).
- **Dockerized setup** — `docker-compose.yml` runs the API and the
  Playwright suite together.

---

## Project Structure

```
vi-sdet-selector/
├─ server/           # FastAPI backend
│  ├─ rules.py       # deterministic rule engine
│  ├─ reasoning.py   # optional Claude explanation layer
│  └─ app.py         # /predict + /predict/explain
├─ playwright-sdk/   # TypeScript SDK + example Playwright test
├─ tests/            # pytest (rule engine, API) + DeepEval (explanations)
├─ model/, data/     # placeholders — no ML model currently in use
├─ .github/workflows/ # CI: pytest + SDK typecheck
├─ Dockerfile/
├─ docker-compose.yml
├─ requirements.txt      # runtime
├─ requirements-dev.txt  # + pytest, httpx, deepeval
└─ conftest.py
```

---

## Quickstart

### 1. Clone and install

```bash
git clone https://github.com/ViviDickens/Vi-Sdet-Selector.git
cd vi-sdet-selector
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash; use venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt   # or requirements.txt to run the API only
```

### 2. Run the API

```bash
uvicorn server.app:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive Swagger UI, or:

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"tag":"button","data_testid":"submit-btn","aria_label":"Submit form","classes":["css-1a2b3c"],"xpath":"//div[2]/button[3]"}'
```

### 3. Run the tests

```bash
python -m pytest tests/ -v   # deterministic, no API key needed
```

`tests/test_rules.py` (rule engine) and `tests/test_api.py` (endpoints)
run everywhere. Both run in CI on every push, along with a typecheck of
the TypeScript SDK.

`tests/test_deepeval_reasoning.py` also needs `ANTHROPIC_API_KEY` (to
generate the explanation) and `OPENAI_API_KEY` (DeepEval's default
judge model) — see `.env.example`. It skips cleanly if either is
missing.

### 4. Run the Playwright SDK demo

With the API running (step 2), in another terminal:

```bash
cd playwright-sdk
npm install
npx playwright install   # first time only
npm test
```

### 5. Or run everything with Docker

```bash
docker compose up --build
```

---

## Tech Stack

- **Backend**: Python 3.11, FastAPI, Pydantic
- **AI layer**: Claude API (explanation generation), DeepEval
  (faithfulness/relevancy testing)
- **SDK**: TypeScript, Playwright
- **Infra**: Docker, Docker Compose

## Roadmap

- [x] GitHub Actions CI (unit tests on every push)
- [ ] Allure reporting for the Playwright suite
- [ ] Revisit a learned component if the rule engine's coverage stops
      scaling

## License

MIT
