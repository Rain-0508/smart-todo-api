# Self-Healing Test Analysis

## Goal

This test is designed to avoid failing immediately when the API response changes small field names.

## Self-healing behavior

The script first looks for the expected response fields:

- `priority`
- `confidence`

If a field is missing, it automatically tries fallback names:

- For priority: `level`, `urgency`, `rank`
- For confidence: `probability`, `score`, `certainty`

If a fallback field is found, the test logs a warning and continues.
If no matching field is found, the test fails with a clear error.

## Execution result

- Live API test status: `passed`
- `/health` returned `200` with `{"status": "ok"}`
- `/predict` returned `200`
- Resolved priority field: `priority`
- Resolved confidence field: `confidence`
- Predicted priority: `High`
- Confidence: `0.63`

## Self-healing verification

The script also ran built-in alias checks to prove the healing logic works:

- `{"level": "Medium", "confidence": 0.51}` was accepted by falling back from `priority` to `level`
- `{"urgency": "Low", "score": 0.18}` was accepted by falling back from `priority` to `urgency` and from `confidence` to `score`

These fallback cases produced warnings instead of failing the whole test.

## Conclusion

The self-healing script works as required. It passes against the current API, detects renamed fields, uses alternative names automatically, and only fails when no valid replacement field can be found.