# Smart Todo API

This project is a small AI-powered task priority app built in three phases:

1. Build a labeled dataset and train a simple machine learning model.
2. Expose the model through a Flask API.
3. Test the API with K6 load tests and a self-healing test script.

The API accepts a task such as `Fix production bug` and returns a predicted priority with a confidence score.

## Project summary

### Phase 1: AI API

- Dataset: `200` labeled tasks in [tasks.csv](tasks.csv)
- Labels: `High`, `Medium`, `Low`
- Model: `TfidfVectorizer + LogisticRegression`
- Training implementation: [src/train_model.py](src/train_model.py)
- Trained model file: [artifacts/model.joblib](artifacts/model.joblib)
- Training metrics: [artifacts/model_metrics.json](artifacts/model_metrics.json)
- Achieved accuracy: `77.5%`

### Phase 2: Performance testing

- Ramp-up implementation: [tests/load/ramp_up_test_impl.js](tests/load/ramp_up_test_impl.js)
- Spike test implementation: [tests/load/spike_test_impl.js](tests/load/spike_test_impl.js)
- Reports: [reports](reports)

### Phase 3: Self-healing test

- Self-healing implementation: [tests/self_healing_test_impl.py](tests/self_healing_test_impl.py)
- Structured report: [reports/self_healing_report.json](reports/self_healing_report.json)
- Analysis: [reports/self_healing_analysis.md](reports/self_healing_analysis.md)

## Reading order

- Start with [README.md](README.md) for setup and project outcome.
- Use [docs/SUBMISSION_MAP.md](docs/SUBMISSION_MAP.md) to review deliverables by category.
- Use [docs/CODE_WALKTHROUGH.md](docs/CODE_WALKTHROUGH.md) for the most important code sections and how to explain them.

## Project structure

- [tasks.csv](tasks.csv): labeled training dataset
- [requirements.txt](requirements.txt): Python dependencies
- [src](src): main Python implementation files
- [tests](tests): load-test and self-healing implementations
- [artifacts](artifacts): generated model artifacts and training metrics
- [reports](reports): generated test outputs and analysis files
- [docs](docs): walkthrough notes and submission navigation

## Setup

### 1. Install Python dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 2. Train the model

```bash
python3 src/train_model.py
```

Expected result:

- Reads [tasks.csv](tasks.csv)
- Trains a classifier
- Writes [artifacts/model.joblib](artifacts/model.joblib)
- Writes [artifacts/model_metrics.json](artifacts/model_metrics.json)

### 3. Start the Flask API

```bash
python3 src/app.py
```

The API runs on `http://127.0.0.1:5000`.

## API endpoints

### `GET /health`

Response:

```json
{
  "status": "ok"
}
```

### `POST /predict`

Request:

```json
{
  "task": "Prepare quarterly report"
}
```

Response example:

```json
{
  "priority": "High",
  "confidence": 0.82
}
```

Validation rules:

- Request body must be JSON
- Field `task` must exist
- Field `task` must be a non-empty string

## Manual API test

### Health check

```bash
curl http://127.0.0.1:5000/health
```

### Prediction

```bash
curl -X POST http://127.0.0.1:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"task":"Fix production bug"}'
```

## Performance testing with K6

Install K6 on macOS:

```bash
brew install k6
```

### Ramp-up test

Run:

```bash
k6 run tests/load/ramp_up_test_impl.js
```

Generated files:

- [reports/ramp_up_output.txt](reports/ramp_up_output.txt)
- [reports/ramp_up_summary.json](reports/ramp_up_summary.json)
- [reports/ramp_up_analysis.md](reports/ramp_up_analysis.md)

Observed results:

- Total requests: `2876`
- Failure rate: `0.00%`
- Average response time: `3.39 ms`
- P95 response time: `6.79 ms`
- Max concurrent users: `50`

Interpretation:

- No obvious slowdown between `1`, `10`, and `50` users
- No request failures during the test

### Spike test

Run:

```bash
k6 run tests/load/spike_test_impl.js
```

Generated files:

- [reports/spike_output.txt](reports/spike_output.txt)
- [reports/spike_summary.json](reports/spike_summary.json)
- [reports/spike_analysis.md](reports/spike_analysis.md)

Observed results:

- Total requests: `5786`
- Failure rate: `0.00%`
- Average response time: `3.15 ms`
- P95 response time: `5.87 ms`
- Max concurrent users: `100`

Interpretation:

- The API did not crash during the sudden jump from `5` to `100` users
- The API recovered correctly after traffic dropped back down

## Self-healing test

Run:

```bash
python3 tests/self_healing_test_impl.py
```

Generated files:

- [reports/self_healing_output.txt](reports/self_healing_output.txt)
- [reports/self_healing_report.json](reports/self_healing_report.json)
- [reports/self_healing_analysis.md](reports/self_healing_analysis.md)

What it does:

- Calls `/health` and `/predict`
- Tries expected fields first
- Falls back to alternative names if needed
- Logs warnings when a fallback field is used
- Fails only when no valid replacement field is found

Current fallback rules:

- Priority field: `priority`, `level`, `urgency`, `rank`
- Confidence field: `confidence`, `probability`, `score`, `certainty`

Observed result:

- Live API test passed
- Current API still returns `priority` and `confidence`
- Built-in alias checks confirmed fallback behavior works

## Final conclusion

This project successfully completes all three phases of the capstone:

1. A labeled dataset and ML model were created.
2. A Flask API was built and validated.
3. Load tests and a self-healing test were implemented and executed.

The current local implementation is stable under the tested traffic levels and includes a resilient test script that can tolerate small response-field changes.