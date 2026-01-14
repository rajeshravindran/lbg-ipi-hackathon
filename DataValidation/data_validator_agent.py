
#!/usr/bin/env python3
"""
ADK Data Validator Agent
------------------------
Validates wallet/customer records against a JSON Schema, enforces null policy,
and checks pipeline timestamps (monotonic order, SLO lags, future skew, watermark).
Finally, a Gemini LLM agent produces human-grade explanations and remediation steps.

Folders (relative to THIS FILE):
  ./data/input/       # JSON inputs
  ./schemas/wallet_v2.json  # JSON Schema

Workflow (SequentialAgent):
  1) InputLoaderAgent       -> state['schema'], state['record'], state['selected_file']
  2) SchemaValidatorAgent   -> state['schema_issues']
  3) NullPolicyAgent        -> state['null_issues']
  4) TimestampValidatorAgent-> state['timestamp_issues'], state['timestamp_metrics']
  5) AggregateAgent         -> state['validation_summary']
  6) ExplanationAgent (LLM) -> human-friendly explanations + remediation plan

Requires: google-adk, jsonschema
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, AsyncGenerator
from pathlib import Path

# jsonschema for Draft 2020-12
try:
    from jsonschema import Draft202012Validator, FormatChecker
except Exception:
    Draft202012Validator = None
    FormatChecker = None

# --- ADK imports (current paths) ---
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions  # instantiate with kwargs

# =========================
# Project paths
# =========================
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "data" / "input"
SCHEMA_PATH = BASE_DIR / "schemas" / "wallet_v2.json"

# =========================
# Policy configuration
# =========================
DEFAULT_CRITICAL_PATHS: List[str] = [
    "wallet_id",
    "customer_id",
    "address.line1",
    "address.city",
    "address.postal_code",
    "address.country_code",
]

DEFAULT_TOLERANCES: Dict[str, float] = {
    "event_to_publish_sec": 300.0,
    "publish_to_validate_sec": 120.0,
    "validate_to_commit_sec": 60.0,
    "future_skew_sec": 120.0,
    "watermark_hours": 24.0,
}

NULL_EQUIVALENTS = {"", " ", "N/A", "UNKNOWN", None}

# =========================
# Helpers
# =========================
def load_json_local(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def looks_like_json_file(path: Path) -> bool:
    if path.suffix.lower() == ".json":
        return True
    try:
        with open(path, "r", encoding="utf-8") as f:
            head = f.read(1)
            return head in ("{", "[")
    except Exception:
        return False

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

def collect_null_policy_issues(record: Dict[str, Any], critical_paths: List[str]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    for path in critical_paths:
        val = get_path_value(record, path)
        if is_null_equiv(val):
            issues.append({
                "category": "unexpected_null",
                "field_path": path,
                "observed_value": None if val is None else str(val),
                "detail": "Null-equivalent value found on a mandatory path",
                "severity": "high",
            })
    return issues

def iter_contract_issues_full(record: Dict[str, Any], schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    if Draft202012Validator is None or FormatChecker is None:
        raise RuntimeError("jsonschema package is required for schema validation but was not found.")
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
            "severity": severity,
        })
    return issues

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
    now_utc: Optional[datetime] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    now_utc = now_utc or datetime.now(timezone.utc)
    issues: List[Dict[str, Any]] = []
    metrics: Dict[str, Any] = {}
    raw = {
        "source_event_time": record.get("source_event_time"),
        "pubsub_publish_time": record.get("pubsub_publish_time"),
        "validator_start_time": record.get("validator_start_time"),
        "commit_time": record.get("commit_time"),
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
            "detail": {"invalid_or_missing": invalid_fields},
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
        "validate_to_commit": l3,
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
            "detail": {"source_event_time": s.isoformat(), "validator_start_time": v.isoformat()},
        })

    watermark_cutoff = now_utc - timedelta(hours=tolerances["watermark_hours"])
    if s < watermark_cutoff:
        issues.append({
            "category": "late_data_beyond_watermark",
            "severity": "low",
            "detail": {"source_event_time": s.isoformat(), "watermark_cutoff": watermark_cutoff.isoformat()},
        })

    metrics["availability"] = {k: True for k in raw.keys()}
    return issues, metrics

# =========================
# Deterministic Agents (implement _run_async_impl)
# =========================
class InputLoaderAgent(BaseAgent):
    name: str = "input_loader"
    description: str = "Loads schema and input record from local project folders."

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state

        if not SCHEMA_PATH.is_file():
            # Emit an informational event (no state change)—LLM will summarize later.
            yield Event(author=self.name, actions=EventActions())
            return

        schema = load_json_local(SCHEMA_PATH)
        yield Event(author=self.name, actions=EventActions(state_delta={"schema": schema}))

        if not INPUT_DIR.is_dir():
            yield Event(author=self.name, actions=EventActions())
            return

        candidates = [p for p in INPUT_DIR.iterdir() if p.is_file() and looks_like_json_file(p)]
        if not candidates:
            yield Event(author=self.name, actions=EventActions())
            return

        file_name = state.get("file_name")
        if file_name:
            target = INPUT_DIR / file_name
            if not target.exists():
                yield Event(author=self.name, actions=EventActions())
                return
        else:
            target = sorted(candidates)[0]

        record = load_json_local(target)
        yield Event(author=self.name, actions=EventActions(state_delta={
            "record": record,
            "selected_file": str(target),
            "available_files": [str(p) for p in sorted(candidates)],
        }))
        return

class SchemaValidatorAgent(BaseAgent):
    name: str = "schema_validator"
    description: str = "Validates record against JSON Schema (Draft 2020-12)."

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        record = state.get("record")
        schema = state.get("schema")
        if record is None or schema is None:
            yield Event(author=self.name, actions=EventActions())
            return

        issues = iter_contract_issues_full(record, schema)
        yield Event(author=self.name, actions=EventActions(state_delta={"schema_issues": issues}))
        return

class NullPolicyAgent(BaseAgent):
    name: str = "null_policy_validator"
    description: str = "Checks null policy across critical paths."

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        record = state.get("record")
        critical_paths: List[str] = state.get("critical_paths") or DEFAULT_CRITICAL_PATHS
        if record is None:
            yield Event(author=self.name, actions=EventActions())
            return

        issues = collect_null_policy_issues(record, critical_paths)
        yield Event(author=self.name, actions=EventActions(state_delta={"null_issues": issues}))
        return

class TimestampValidatorAgent(BaseAgent):
    name: str = "timestamp_validator"
    description: str = "Checks monotonic order, SLO lags, future skew, watermark."

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        record = state.get("record")
        tolerances: Dict[str, float] = state.get("tolerances") or DEFAULT_TOLERANCES
        if record is None:
            yield Event(author=self.name, actions=EventActions())
            return

        issues, metrics = check_pipeline_timestamps(record, tolerances)
        yield Event(author=self.name, actions=EventActions(state_delta={
            "timestamp_issues": issues,
            "timestamp_metrics": metrics,
        }))
        return

class AggregateAgent(BaseAgent):
    name: str = "aggregate_validator_results"
    description: str = "Aggregates issues from agents into validation_summary."

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        record = state.get("record") or {}
        schema_issues = state.get("schema_issues") or []
        null_issues = state.get("null_issues") or []
        ts_issues = state.get("timestamp_issues") or []
        ts_metrics = state.get("timestamp_metrics") or {}

        issues = schema_issues + null_issues + ts_issues
        ok = len(issues) == 0
        summary = {
            "counts": {
                "schema_issues": len(schema_issues),
                "null_issues": len(null_issues),
                "timestamp_issues": len(ts_issues),
                "total": len(issues),
            },
            "timestamp_metrics": ts_metrics,
            "record_hint": record.get("wallet_id") or record.get("customer_id") or "<unknown>",
            "selected_file": state.get("selected_file"),
        }
        yield Event(author=self.name, actions=EventActions(state_delta={
            "validation_summary": {"ok": ok, "issues": issues, "summary": summary}
        }))
        return

# =========================
# LLM Agent (Gemini) for explanations
# =========================
_gemini_model = Gemini(
    model="gemini-2.5-flash",
    use_interactions_api=True,
)

ExplanationAgent = LlmAgent(
    name="dq_explanation_agent",
    description="Explains validation failures and provides remediation suggestions.",
    model=_gemini_model,
    instruction=(
        """
You are a data quality validator/explainer for wallet/customer records.
You are given a validation summary with detailed issues from deterministic tools.

Tasks:
1) Explain each issue in human-friendly terms (why it failed).
2) Provide concrete remediation steps (how to fix), with examples.
3) Propose safe, minimal transformations (uppercase ISO country codes, case-fold enums,
   convert currency strings to numeric) without contradicting hard rules.
4) Output BOTH:
   (a) a brief human-readable summary, and
   (b) a structured JSON:
       {
         "explanations": [{"field_path","category","severity","why","how_to_fix"}],
         "remediation_plan": [{"priority","step","example"}],
         "compliance_status": {"ok", "summary"}
       }

Validation summary:
{validation_summary}
        """
    ),
)

# =========================
# Root workflow (SequentialAgent)
# =========================
root_agent = SequentialAgent(
    name="wallet_contract_validation_workflow",
    description="InputLoader → JSON Schema → Null policy → Timestamps → Aggregate → LLM explanation",
    sub_agents=[
        InputLoaderAgent(),
        SchemaValidatorAgent(),
        NullPolicyAgent(),
        TimestampValidatorAgent(),
        AggregateAgent(),
        ExplanationAgent,
    ],
)

# =========================
# Optional helper (programmatic seeding)
# =========================
async def seed_state_from_strings(
    ctx: InvocationContext,
    record_json_str: str,
    schema_json_str: str,
    critical_paths: Optional[List[str]] = None,
    tolerances: Optional[Dict[str, float]] = None,
    file_name: Optional[str] = None,
) -> None:
    ctx.session.state["record"] = json.loads(record_json_str)
    ctx.session.state["schema"] = json.loads(schema_json_str)
    if critical_paths:
        ctx.session.state["critical_paths"] = critical_paths
    if tolerances:
        ctx.session.state["tolerances"] = tolerances
    if file_name:
        ctx.session.state["file_name"] = file_name
