from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from flask import Flask, jsonify, request
from joblib import load


ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT_DIR / "artifacts" / "model.joblib"

app = Flask(__name__)


@lru_cache(maxsize=1)
def load_model():
    # Cache the model after the first load so each request does not hit disk again.
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Trained model not found. Run `python3 src/train_model.py` before starting the API."
        )
    return load(MODEL_PATH)


def error_response(message: str, status_code: int):
    # Keep error responses consistent so tests and clients can handle them predictably.
    response = jsonify({"error": message})
    response.status_code = status_code
    return response


@app.get("/health")
def health_check():
    # This lightweight endpoint is used by manual checks and automated tests.
    return jsonify({"status": "ok"}), 200


@app.post("/predict")
def predict_priority():
    if not request.is_json:
        return error_response("Request body must be valid JSON.", 400)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("Request body must be a JSON object.", 400)

    task = payload.get("task")
    if not isinstance(task, str) or not task.strip():
        return error_response("Field `task` is required and must be a non-empty string.", 400)

    try:
        # Reuse the trained classifier to predict the label and its highest probability.
        model = load_model()
        clean_task = task.strip()
        priority = model.predict([clean_task])[0]
        probabilities = model.predict_proba([clean_task])[0]
        confidence = float(max(probabilities))
    except FileNotFoundError as exc:
        return error_response(str(exc), 500)
    except Exception:
        return error_response("Prediction failed.", 500)

    return (
        jsonify(
            {
                "priority": priority,
                "confidence": round(confidence, 2),
            }
        ),
        200,
    )


def main() -> None:
    debug_enabled = os.getenv("FLASK_DEBUG", "0") == "1"
    use_reloader = os.getenv("FLASK_USE_RELOADER", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_enabled, use_reloader=use_reloader)


if __name__ == "__main__":
    main()