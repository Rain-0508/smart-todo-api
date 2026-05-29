from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request


ROOT_DIR = Path(__file__).resolve().parent.parent
BASE_URL = "http://127.0.0.1:5000"
REPORT_PATH = ROOT_DIR / "reports" / "self_healing_report.json"
# These aliases define the small response-field changes the test can heal from.
PRIORITY_FIELDS = ["priority", "level", "urgency", "rank"]
CONFIDENCE_FIELDS = ["confidence", "probability", "score", "certainty"]


@dataclass
class ExtractionResult:
    value: Any
    field_name: str
    warnings: list[str]


def http_json(method: str, url: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    # Use the standard library so this script stays dependency-light and easy to run.
    data = None
    headers = {"Content-Type": "application/json"}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(url, data=data, headers=headers, method=method)

    try:
        with request.urlopen(req, timeout=10) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        status_code = exc.code
        body = exc.read().decode("utf-8")
    except error.URLError as exc:
        raise RuntimeError(f"Request to {url} failed: {exc.reason}") from exc

    try:
        parsed_body = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Response from {url} is not valid JSON: {body}") from exc

    if not isinstance(parsed_body, dict):
        raise RuntimeError(f"Response from {url} must be a JSON object.")

    return status_code, parsed_body


def extract_with_aliases(payload: dict[str, Any], canonical_name: str, aliases: list[str]) -> ExtractionResult:
    # Prefer the expected field name, but fall back to known alternatives with warnings.
    warnings: list[str] = []

    if canonical_name in payload:
        return ExtractionResult(payload[canonical_name], canonical_name, warnings)

    for alias in aliases:
        if alias in payload:
            warnings.append(
                f"Field `{canonical_name}` missing. Fell back to `{alias}` automatically."
            )
            return ExtractionResult(payload[alias], alias, warnings)

    attempted_fields = ", ".join([canonical_name, *aliases])
    raise AssertionError(f"Missing expected field. Tried: {attempted_fields}")


def validate_priority(value: Any) -> str:
    # Keep the accepted labels aligned with the model's training targets.
    allowed_values = {"High", "Medium", "Low"}
    if not isinstance(value, str) or value not in allowed_values:
        raise AssertionError(
            "Priority value must be one of High, Medium, Low. "
            f"Received: {value!r}"
        )
    return value


def validate_confidence(value: Any) -> float:
    # Confidence should remain a normalized numeric score for downstream consumers.
    if not isinstance(value, (int, float)):
        raise AssertionError(f"Confidence value must be numeric. Received: {value!r}")

    confidence = float(value)
    if not 0.0 <= confidence <= 1.0:
        raise AssertionError(f"Confidence must be between 0 and 1. Received: {confidence}")

    return confidence


def run_live_api_test(base_url: str) -> dict[str, Any]:
    # First verify the service is alive, then validate the real prediction response.
    health_status, health_body = http_json("GET", f"{base_url}/health")
    if health_status != 200 or health_body.get("status") != "ok":
        raise AssertionError(f"Health check failed: status={health_status}, body={health_body}")

    predict_status, predict_body = http_json(
        "POST",
        f"{base_url}/predict",
        payload={"task": "Fix production bug"},
    )
    if predict_status != 200:
        raise AssertionError(f"Predict request failed: status={predict_status}, body={predict_body}")

    priority_result = extract_with_aliases(predict_body, "priority", PRIORITY_FIELDS[1:])
    confidence_result = extract_with_aliases(
        predict_body,
        "confidence",
        CONFIDENCE_FIELDS[1:],
    )

    priority = validate_priority(priority_result.value)
    confidence = validate_confidence(confidence_result.value)

    return {
        "health": {
            "status_code": health_status,
            "body": health_body,
        },
        "predict": {
            "status_code": predict_status,
            "body": predict_body,
            "resolved_priority_field": priority_result.field_name,
            "resolved_confidence_field": confidence_result.field_name,
            "priority": priority,
            "confidence": confidence,
            "warnings": priority_result.warnings + confidence_result.warnings,
        },
    }


def run_alias_self_checks() -> list[dict[str, Any]]:
    # These synthetic samples prove the fallback logic without changing the live API.
    samples = [
        {
            "name": "canonical_fields",
            "payload": {"priority": "High", "confidence": 0.87},
        },
        {
            "name": "priority_alias_fields",
            "payload": {"level": "Medium", "confidence": 0.51},
        },
        {
            "name": "multiple_alias_fields",
            "payload": {"urgency": "Low", "score": 0.18},
        },
    ]

    results: list[dict[str, Any]] = []

    for sample in samples:
        priority_result = extract_with_aliases(sample["payload"], "priority", PRIORITY_FIELDS[1:])
        confidence_result = extract_with_aliases(sample["payload"], "confidence", CONFIDENCE_FIELDS[1:])

        results.append(
            {
                "sample": sample["name"],
                "payload": sample["payload"],
                "resolved_priority_field": priority_result.field_name,
                "resolved_confidence_field": confidence_result.field_name,
                "priority": validate_priority(priority_result.value),
                "confidence": validate_confidence(confidence_result.value),
                "warnings": priority_result.warnings + confidence_result.warnings,
            }
        )

    return results


def main() -> int:
    # Capture both live results and fallback demonstrations in one shareable report.
    report = {
        "base_url": BASE_URL,
        "self_healing_rules": {
            "priority": PRIORITY_FIELDS,
            "confidence": CONFIDENCE_FIELDS,
        },
    }

    live_result = run_live_api_test(BASE_URL)
    alias_results = run_alias_self_checks()

    report["live_api_test"] = live_result
    report["alias_self_checks"] = alias_results
    report["status"] = "passed"

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Self-healing test passed.")
    print(f"Health endpoint status: {live_result['health']['status_code']}")
    print(
        "Predict endpoint resolved fields: "
        f"priority={live_result['predict']['resolved_priority_field']}, "
        f"confidence={live_result['predict']['resolved_confidence_field']}"
    )
    print(f"Priority value: {live_result['predict']['priority']}")
    print(f"Confidence value: {live_result['predict']['confidence']:.2f}")
    print(f"Report saved to: {REPORT_PATH.relative_to(ROOT_DIR)}")

    alias_warnings = sum(len(item["warnings"]) for item in alias_results)
    print(f"Alias self-check warnings observed: {alias_warnings}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Self-healing test failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc