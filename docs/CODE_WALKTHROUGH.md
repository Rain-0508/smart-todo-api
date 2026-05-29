# Code Walkthrough

## Project structure

This project now separates implementation from entrypoints so the structure is easier to read without breaking the original commands.

- `tasks.csv`: labeled training dataset
- `src/`: main Python implementation
- `tests/`: load-test and self-healing implementations
- `artifacts/`: generated model files and training metrics
- `reports/`: generated outputs and analysis documents
- `docs/`: human-readable project walkthroughs and learning notes

## How the project flows end to end

1. `tasks.csv` stores manually labeled task examples.
2. `src/train_model.py` reads the CSV, trains a text classifier, and saves artifacts.
3. `src/app.py` loads the trained model and exposes `/health` and `/predict`.
4. `tests/load/*.js` test API behavior under traffic.
5. `tests/self_healing_test_impl.py` checks that the API still works even if response field names change slightly.
6. Commands now run directly from `src/` and `tests/`.

## Key code section 1: loading and cleaning the dataset

File: [src/train_model.py](../src/train_model.py)

```python
def load_dataset(dataset_path: Path) -> tuple[list[str], list[str]]:
    with dataset_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        tasks: list[str] = []
        labels: list[str] = []

        for row in reader:
            task = (row.get("task") or "").strip()
            priority = (row.get("priority") or "").strip()
            if not task or not priority:
                continue
            tasks.append(task)
            labels.append(priority)
```

Why it matters:

- This is the entry point for model training.
- It reads the CSV into two aligned arrays: task text and labels.
- It skips incomplete rows instead of crashing, which makes the training script more robust.

What to explain in a demo:

- The model cannot train until text and labels are separated cleanly.
- This function is where raw CSV data becomes usable training data.

## Key code section 2: text vectorization and classification pipeline

File: [src/train_model.py](../src/train_model.py)

```python
def build_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            (
                "vectorizer",
                TfidfVectorizer(lowercase=True, ngram_range=(1, 2), stop_words="english"),
            ),
            (
                "classifier",
                LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
            ),
        ]
    )
```

Why it matters:

- `TfidfVectorizer` converts human language into numeric features.
- `LogisticRegression` learns how those features map to `High`, `Medium`, and `Low`.
- This is the core machine learning logic of the project.

What to explain in a demo:

- The project does not use embeddings or deep learning.
- It uses a simple and beginner-friendly classical ML pipeline.
- `ngram_range=(1, 2)` allows the model to learn from both single words and short phrases.

## Key code section 3: train/test split and evaluation

File: [src/train_model.py](../src/train_model.py)

```python
X_train, X_test, y_train, y_test = train_test_split(
    tasks,
    labels,
    test_size=0.2,
    random_state=RANDOM_STATE,
    stratify=labels,
)

pipeline.fit(X_train, y_train)

predictions = pipeline.predict(X_test)
accuracy = accuracy_score(y_test, predictions)
```

Why it matters:

- The split keeps part of the data unseen so accuracy is meaningful.
- `stratify=labels` preserves class balance across the split.
- This is how the project confirms that the model reaches the required `~70%` accuracy target.

What to explain in a demo:

- Training accuracy alone is not enough.
- The test set simulates unseen examples.
- The achieved result was `77.5%`, which satisfies the requirement.

## Key code section 4: prediction endpoint in Flask

File: [src/app.py](../src/app.py)

```python
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
```

Why it matters:

- This code protects the API from invalid input.
- It returns clean `400` errors instead of producing unclear failures deeper in the stack.

What to explain in a demo:

- Good APIs validate input before calling the model.
- This makes testing and debugging much easier.

## Key code section 5: model inference and confidence extraction

File: [src/app.py](../src/app.py)

```python
model = load_model()
clean_task = task.strip()
priority = model.predict([clean_task])[0]
probabilities = model.predict_proba([clean_task])[0]
confidence = float(max(probabilities))
```

Why it matters:

- `predict()` returns the final label.
- `predict_proba()` returns class probabilities.
- The highest probability is used as the confidence score shown to the user.

What to explain in a demo:

- The API returns more than a class label.
- Confidence helps the user understand how certain the model is.

## Key code section 6: K6 response validation

File: [tests/load/ramp_up_test_impl.js](../tests/load/ramp_up_test_impl.js) and [tests/load/spike_test_impl.js](../tests/load/spike_test_impl.js)

```javascript
check(response, {
  'predict status is 200': (res) => res.status === 200,
  'predict returns priority': (res) => {
    const body = res.json();
    return body && typeof body.priority === 'string' && body.priority.length > 0;
  },
  'predict returns confidence': (res) => {
    const body = res.json();
    return body && typeof body.confidence === 'number';
  },
});
```

Why it matters:

- The performance tests check both speed and API correctness.
- A fast API is not enough if the response shape is broken.

What to explain in a demo:

- Load testing should validate output, not only timing.
- Both K6 scripts reuse the same correctness checks so the results are comparable.

## Key code section 7: self-healing fallback logic

File: [tests/self_healing_test_impl.py](../tests/self_healing_test_impl.py)

```python
def extract_with_aliases(payload: dict[str, Any], canonical_name: str, aliases: list[str]) -> ExtractionResult:
    warnings: list[str] = []

    if canonical_name in payload:
        return ExtractionResult(payload[canonical_name], canonical_name, warnings)

    for alias in aliases:
        if alias in payload:
            warnings.append(
                f"Field `{canonical_name}` missing. Fell back to `{alias}` automatically."
            )
            return ExtractionResult(payload[alias], alias, warnings)
```

Why it matters:

- This is the core of the self-healing test.
- It lets the script continue when a response field is renamed in a small, expected way.
- It does not hide the change; it records a warning so the drift is visible.

What to explain in a demo:

- Normal tests fail immediately when field names change.
- This script first tries the expected name, then tries known alternatives.
- It only fails when none of the fallback names exist.

## Key code section 8: live API test plus internal fallback verification

File: [tests/self_healing_test_impl.py](../tests/self_healing_test_impl.py)

```python
live_result = run_live_api_test(BASE_URL)
alias_results = run_alias_self_checks()
```

Why it matters:

- The script does not rely only on synthetic examples.
- It validates the real running API and also proves the fallback behavior with controlled payloads.

What to explain in a demo:

- The live API still returns `priority` and `confidence` today.
- The internal checks prove the healing behavior would still work if the field names changed later.

## Recommended explanation order for a demo

1. Start with the dataset and why labels matter.
2. Move to the ML pipeline and evaluation.
3. Show the Flask API and input validation.
4. Show load testing and what the metrics mean.
5. End with the self-healing logic because it is the most distinctive testing feature.