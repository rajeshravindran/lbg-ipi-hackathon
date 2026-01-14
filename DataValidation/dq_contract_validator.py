
#!/usr/bin/env python3
"""
Full Data Contract Validator (local folders; strict timestamps present)

- JSON Schema (Draft 2020-12): required, type, enum, format, additionalProperties=false
- Non-null policy on critical paths
- Pipeline timestamps: ALL must be present & valid ISO 8601
  * Monotonic: source ≤ publish ≤ validate ≤ commit
  * Lag SLOs: event→publish, publish→validate, validate→commit
  * Future skew: source not ahead of validate beyond tolerance
  * Watermark: source not older than watermark window

Paths are resolved relative to THIS FILE's directory:
  BASE_DIR = <.../LBG-IPI-HACKATHON/DataValidation>
  INPUT_DIR = BASE_DIR / "data" / "input"
  SCHEMA_PATH = BASE_DIR / "schemas" / "wallet_v2.json"
"""

import os
import sys
import json
from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---- Dependencies: pip install jsonschema ----
from jsonschema import Draft202012Validator, FormatChecker

# =========================
# Path configuration (UPDATED)
# =========================
BASE_DIR = Path(__file__).resolve().parent  # .../LBG-IPI-HACKATHON/DataValidation
INPUT_DIR = BASE_DIR / "data" / "input"     # .../DataValidation/data/input
SCHEMA_PATH = BASE_DIR / "schemas" / "wallet_v2.json"  # .../DataValidation/schemas/wallet_v2.json

# =========================
# Hardcoded policy/config
# =========================
CRITICAL_PATHS = [
    "wallet_id",
    "customer_id",
    "address.line1",
    "address.city",
    "address.postal_code",
    "address.country_code",
]

TOLERANCES = {
    "event_to_publish_sec":    300.0,  # ≤ 5 minutes
    "publish_to_validate_sec": 120.0,  # ≤ 2 minutes
    "validate_to_commit_sec":   60.0,  # ≤ 1 minute
    "future_skew_sec":         120.0,  # source not > validate by more than 2 min
    "watermark_hours":          24.0,  # event not older than 24 hours
}

# =========================
# Null policy helpers
# =========================
NULL_EQUIVALENTS = {"", " ", "N/A", "UNKNOWN", None}

def is_null_equiv(val: Any) -> bool:
    return (val in NULL_EQUIVALENTS) or (isinstance(val, str) and val.strip() == "")

def get_path_value(obj: Any, path: str) -> Any:
    current = obj
    for key in path.split("."):
        if isinstance(current, dict):
            if key in current:
                current = current[key]
            else:
                return None
        elif isinstance(current, list):
            try:
                idx = int(key)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            except ValueError:
                return None
        else:
            return None
    return current

def check_null_policy(record: Dict[str, Any], critical_paths: List[str]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    for path in critical_paths:
        val = get_path_value(record, path)
        if is_null_equiv(val):
            issues.append({
                "category": "unexpected_null",
                "field_path": path,
                "observed_value": None if val is None else str(val),
                "detail": "Null-equivalent value found on a mandatory path",
                "severity": "high"
            })
    return issues

# =========================
# JSON Schema validation
# =========================
def iter_contract_issues_full(record: Dict[str, Any], schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Collect ALL schema violations using Draft202012Validator.iter_errors + FormatChecker:
      - required, type, enum, format, additionalProperties
      - other validators as 'contract_violation'
    """
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    issues: List[Dict[str, Any]] = []
    for e in validator.iter_errors(record):
        if e.validator == "required":
            cat, severity = "missing_required", "high"
        elif e.validator == "type":
            cat, severity = "type_mismatch", "high"
        elif e.validator == "enum":
            cat, severity = "enum_violation", "medium"
        elif e.validator == "format":
            cat, severity = "format_violation", "medium"
        elif e.validator == "additionalProperties":
            cat, severity = "schema_drift_additive", "medium"
        else:
            cat, severity = "contract_violation", "medium"

        path_str = ".".join(str(p) for p in e.path)
        issues.append({
            "category": cat,
            "field_path": path_str,
            "detail": e.message,
            "validator": e.validator,
            "severity": severity
        })
    return issues

# =========================
# Timestamp checks
# =========================
def parse_ts(ts_str: Any) -> Optional[datetime]:
    if not isinstance(ts_str, str) or ts_str.strip() == "":
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None

def check_pipeline_timestamps(
    record: Dict[str, Any],
    tolerances: Dict[str, float],
    now_utc: datetime,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Strict timestamp checks: ALL four must parse successfully.
    Monotonic order, lags, future skew, watermark.
    """
    issues: List[Dict[str, Any]] = []
    metrics: Dict[str, Any] = {}

    raw = {
        "source_event_time":   record.get("source_event_time"),
        "pubsub_publish_time": record.get("pubsub_publish_time"),
        "validator_start_time":record.get("validator_start_time"),
        "commit_time":         record.get("commit_time"),
    }
    s = parse_ts(raw["source_event_time"])
    p = parse_ts(raw["pubsub_publish_time"])
    v = parse_ts(raw["validator_start_time"])
    c = parse_ts(raw["commit_time"])

    invalid_fields = {k: raw[k] for k, dt in zip(raw.keys(), [s, p, v, c]) if dt is None}
    if invalid_fields:
        issues.append({
            "category": "timestamp_parse_error",
            "severity": "high",
            "detail": {"invalid_or_missing": invalid_fields}
        })
        metrics["availability"] = {k: (parse_ts(raw[k]) is not None) for k in raw.keys()}
        metrics["lags_sec"] = {}
        return issues, metrics

    def mono_violation(detail: Dict[str, str]):
        issues.append({"category": "timestamp_monotonic_violation", "severity": "medium", "detail": detail})

    if s > p:
        mono_violation({"source_event_time": s.isoformat(), "pubsub_publish_time": p.isoformat()})
    if p > v:
        mono_violation({"pubsub_publish_time": p.isoformat(), "validator_start_time": v.isoformat()})
    if v > c:
        mono_violation({"validator_start_time": v.isoformat(), "commit_time": c.isoformat()})

    l1 = (p - s).total_seconds()
    l2 = (v - p).total_seconds()
    l3 = (c - v).total_seconds()

    metrics["lags_sec"] = {
        "event_to_publish": l1,
        "publish_to_validate": l2,
        "validate_to_commit": l3
    }

    if l1 > tolerances["event_to_publish_sec"]:
        issues.append({"category": "lag_slo_breach_event_to_publish", "severity": "medium", "detail": {"lag_sec": l1}})
    if l2 > tolerances["publish_to_validate_sec"]:
        issues.append({"category": "lag_slo_breach_publish_to_validate", "severity": "medium", "detail": {"lag_sec": l2}})
    if l3 > tolerances["validate_to_commit_sec"]:
        issues.append({"category": "lag_slo_breach_validate_to_commit", "severity": "low", "detail": {"lag_sec": l3}})

    if (s - v).total_seconds() > tolerances["future_skew_sec"]:
        issues.append({
            "category": "future_time_skew",
            "severity": "medium",
            "detail": {"source_event_time": s.isoformat(), "validator_start_time": v.isoformat()}
        })

    watermark_cutoff = now_utc - timedelta(hours=tolerances["watermark_hours"])
    if s < watermark_cutoff:
        issues.append({
            "category": "late_data_beyond_watermark",
            "severity": "low",
            "detail": {"source_event_time": s.isoformat(), "watermark_cutoff": watermark_cutoff.isoformat()}
        })

    metrics["availability"] = {k: True for k in raw.keys()}
    return issues, metrics

# =========================
# IO + orchestration
# =========================
def load_json_local(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def looks_like_json_file(path: Path) -> bool:
    """
    Accept *.json files. If no extension, allow if file is text and begins with { or [.
    This helps with files like 'user_timestamp_breach' seen in the repo.
    """
    if path.suffix.lower() == ".json":
        return True
    try:
        with open(path, "r", encoding="utf-8") as f:
            head = f.read(1)
            return head in ("{", "[")
    except Exception:
        return False

def validate_one_record(record: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    schema_issues = iter_contract_issues_full(record, schema)
    null_issues = check_null_policy(record, CRITICAL_PATHS)

    now_utc = datetime.now(timezone.utc)
    ts_issues, ts_metrics = check_pipeline_timestamps(record, TOLERANCES, now_utc)

    issues = schema_issues + null_issues + ts_issues
    ok = len(issues) == 0
    result = {
        "ok": ok,
        "record_hint": record.get("wallet_id") or record.get("customer_id") or "<unknown>",
        "issues": issues,
        "summary": {
            "counts": {
                "schema_issues": len(schema_issues),
                "null_issues": len(null_issues),
                "timestamp_issues": len(ts_issues)
            },
            "timestamp_metrics": ts_metrics
        }
    }
    return result

def main():
    # Load schema
    try:
        schema = load_json_local(SCHEMA_PATH)
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"Failed to load schema '{SCHEMA_PATH}': {e}"}), flush=True)
        sys.exit(2)

    # Ensure input dir exists
    if not INPUT_DIR.is_dir():
        print(json.dumps({"ok": False, "error": f"INPUT_DIR not found: {INPUT_DIR}"}), flush=True)
        sys.exit(2)

    # Find candidate files (accept *.json and JSON-looking files without extension)
    files = [p for p in INPUT_DIR.iterdir() if p.is_file() and looks_like_json_file(p)]
    if not files:
        print(json.dumps({"ok": True, "message": f"No JSON files found in {INPUT_DIR}"}), flush=True)
        sys.exit(0)

    any_fail = False
    aggregate = {
        "total_files": len(files),
        "valid_files": 0,
        "invalid_files": 0,
        "by_file": {}
    }

    for path in sorted(files):
        try:
            record = load_json_local(path)
        except Exception as e:
            result = {"ok": False, "error": f"Failed to load JSON '{path}': {e}"}
            print(json.dumps({"file": str(path), "result": result}, indent=2), flush=True)
            any_fail = True
            aggregate["by_file"][str(path)] = result
            continue

        result = validate_one_record(record, schema)
        print(json.dumps({"file": str(path), "result": result}, indent=2), flush=True)

        aggregate["by_file"][str(path)] = result
        if result["ok"]:
            aggregate["valid_files"] += 1
        else:
            aggregate["invalid_files"] += 1
            any_fail = True

    print(json.dumps({"aggregate_summary": aggregate}, indent=2), flush=True)
    sys.exit(1 if any_fail else 0)

if __name__ == "__main__":
    main()
