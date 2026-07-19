# Model

There's no trained ML model in this project (anymore).

Early versions of this repo planned a scikit-learn classifier
(`train.py` / `evaluate.py` / `model.joblib`) to predict locator
strategies. That approach was dropped in favor of `server/rules.py`: a
deterministic rule engine that's explainable by design and doesn't
need training data, a training pipeline, or a model registry to defend
in an interview.

The only place an LLM is involved is `server/reasoning.py`, which
writes a natural-language explanation from the rule engine's own
signals — validated with DeepEval, not trained.

This folder is kept empty on purpose as a placeholder in case a real
learned component earns its way back in later.
