from __future__ import annotations

import csv
import json
from pathlib import Path

from joblib import dump
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
DATASET_PATH = ROOT_DIR / "tasks.csv"
MODEL_PATH = ARTIFACTS_DIR / "model.joblib"
METRICS_PATH = ARTIFACTS_DIR / "model_metrics.json"
MINIMUM_ACCURACY = 0.70
RANDOM_STATE = 42


def load_dataset(dataset_path: Path) -> tuple[list[str], list[str]]:
    # Read the labeled CSV and ignore any incomplete rows instead of crashing.
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

    if not tasks:
        raise ValueError("Dataset is empty or missing labeled rows.")

    return tasks, labels


def build_pipeline() -> Pipeline:
    # TF-IDF turns task text into numeric features, then logistic regression
    # learns how those features map to High, Medium, and Low priorities.
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


def main() -> None:
    tasks, labels = load_dataset(DATASET_PATH)
    # Stratification preserves the class balance in both train and test splits.
    X_train, X_test, y_train, y_test = train_test_split(
        tasks,
        labels,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=labels,
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    # Evaluate on held-out data so the reported accuracy reflects unseen examples.
    predictions = pipeline.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    report = classification_report(y_test, predictions, output_dict=True)

    # Save both the trained model and the metrics so later phases can reuse them.
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    dump(pipeline, MODEL_PATH)

    metrics = {
        "dataset_size": len(tasks),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "accuracy": round(accuracy, 4),
        "minimum_accuracy": MINIMUM_ACCURACY,
        "meets_minimum": accuracy >= MINIMUM_ACCURACY,
        "labels": sorted(set(labels)),
        "classification_report": report,
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"Dataset rows: {len(tasks)}")
    print(f"Train rows: {len(X_train)}")
    print(f"Test rows: {len(X_test)}")
    print(f"Accuracy: {accuracy:.2%}")
    print(f"Model saved to: {MODEL_PATH.relative_to(ROOT_DIR)}")
    print(f"Metrics saved to: {METRICS_PATH.relative_to(ROOT_DIR)}")

    if accuracy < MINIMUM_ACCURACY:
        raise SystemExit(
            f"Model accuracy {accuracy:.2%} is below the required {MINIMUM_ACCURACY:.0%}."
        )


if __name__ == "__main__":
    main()