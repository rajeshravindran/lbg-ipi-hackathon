
#!/usr/bin/env python3
"""
ADK Data Validator Agent — Batch-first workflow with Gemini explanations (Markdown chat output)
-----------------------------------------------------------------------------------------------
Validates ALL wallet/customer JSON files under ./data/input against a JSON Schema,
enforces null policy, and checks pipeline timestamps. For each input, calls gemini-2.5-flash to generate:
  - Human-friendly English summary
  - Structured remediation plan (JSON)

Writes one uniform output JSON per input to ./data/output AND
also posts a Markdown summary per file in the ADK web chat.

Requires: google-adk, jsonschema
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, AsyncGenerator
from pathlib import Path

# jsonschema for Draft 2020-12
try:
    from jsonschema import Draft202012Validator, FormatChecker
except Exception:
    Draft202012Validator = None
    FormatChecker = None

# --- ADK imports ---
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions  # state updates / control signals

# --- LLM + Content types ---
from google.adk.models.google_llm import Gemini
from google.genai import types  # Content/Part for chat-visible Markdown text

# =========================
# Project paths
# =========================
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "data" / "input"
OUTPUT_DIR = BASE_DIR / "data" / "output"
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
# Output doc schema
# =========================
OUTPUT_DOC_SCHEMA_ID = "adk.wallet.validation.output.v1"

def _build_output_doc(
    input_path: Path,
    record_hint: str,
    counts: Dict[str, int],
    timestamp_metrics: Dict[str, Any],
    issues: List[Dict[str, Any]],
    ok: bool,
    llm_summary_text: str,
    llm_structured: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "$schema": OUTPUT_DOC_SCHEMA_ID,
        "input_file": str(input_path),
        "record_hint": record_hint,
        "ok": ok,
        "counts": counts,
        "issues": issues,
        "timestamp_metrics": timestamp_metrics,
        "llm": {
            "summary_text": llm_summary_text,
            "structured": llm_structured,
        },
    }

# =========================
# Gemini helper (same behavior, better summary)
# =========================
_gemini_model = Gemini(model="gemini-2.5-flash", use_interactions_api=True)

_EXPLANATION_SYSTEM_PROMPT = """You are a data quality validator/explainer for wallet/customer records.

Return your answer in TWO parts:
1) A brief plain-English paragraph beginning with:
   SUMMARY:
   Keep it under 4 sentences, explain what passed/failed and the main reason(s).
   Mention practical remediation actions.
2) A single JSON object with EXACT keys:
   {
     "explanations": [{"field_path":"...", "category":"...", "severity":"...", "why":"...", "how_to_fix":"..."}],
     "remediation_plan": [{"priority":"high|medium|low", "step":"...", "example":"..."}],
     "compliance_status": {"ok": true|false, "summary": "one-sentence status"}
   }
Do NOT include code fences or commentary around the JSON.
"""

def _extract_summary_and_json(text: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    json_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    json_block = json_match.group(0) if json_match else None
    before_json = text[:json_match.start()] if json_block else text
    m = re.search(r"SUMMARY:\s*(.*)", before_json, flags=re.DOTALL)
    summary_text = re.sub(r"\s+", " ", m.group(1).strip()) if m else before_json.strip()
    structured = None
    if json_block:
        try:
            structured = json.loads(json_block)
        except Exception:
            structured = None
    return summary_text, structured

def build_deterministic_summary_text(ok: bool, issues: List[Dict[str, Any]], counts: Dict[str, int]) -> str:
    if ok:
        return "SUMMARY: The record passed all validations. No schema, null, or timestamp issues were found."
    if not issues:
        return "SUMMARY: The record did not pass validation, but no specific issues were enumerated. Re-run validation or check input parsing."
    cats = sorted(set(i.get("category", "issue") for i in issues))
    main = f"SUMMARY: The record failed validation due to: {', '.join(cats)}."
    hints = []
    if counts.get("schema_issues", 0) > 0:
        hints.append("ensure required fields exist, types match, and formats/enums are correct")
    if counts.get("null_issues", 0) > 0:
        hints.append("populate mandatory fields and remove null-equivalent values")
    if counts.get("timestamp_issues", 0) > 0:
        hints.append("fix event/publish/validate/commit ordering, keep lags within SLO, and avoid lateness beyond the watermark")
    rem = (" Suggested remediation: " + "; ".join(hints) + ".") if hints else ""
    return (main + rem).strip()

def invoke_gemini_explanation(validation_summary: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    user_payload = "Validation summary:\n" + json.dumps(validation_summary, indent=2)
    prompt = _EXPLANATION_SYSTEM_PROMPT + "\n\n" + user_payload
    llm_text = ""
    try:
        if hasattr(_gemini_model, "generate"):
            resp = _gemini_model.generate(prompt=prompt)
            llm_text = getattr(resp, "text", None) or (resp if isinstance(resp, str) else json.dumps(resp, ensure_ascii=False))
        elif hasattr(_gemini_model, "generate_content"):
            resp = _gemini_model.generate_content(prompt)
            llm_text = getattr(resp, "text", None) or (resp if isinstance(resp, str) else json.dumps(resp, ensure_ascii=False))
        elif hasattr(_gemini_model, "complete"):
            resp = _gemini_model.complete(prompt=prompt)
            llm_text = getattr(resp, "text", None) or (resp if isinstance(resp, str) else json.dumps(resp, ensure_ascii=False))
        else:
            resp = _gemini_model(prompt) if callable(_gemini_model) else str(validation_summary)
            llm_text = getattr(resp, "text", None) or (resp if isinstance(resp, str) else json.dumps(resp, ensure_ascii=False))
    except Exception as e:
        llm_text = f"LLM call failed: {e}"

    summary_text, structured = _extract_summary_and_json(llm_text)

    ok = bool(validation_summary.get("ok"))
    counts = validation_summary.get("summary", {}).get("counts", {}) or validation_summary.get("counts", {}) or {}
    issues = validation_summary.get("issues", [])

    def looks_like_dict_dump(s: str) -> bool:
        return bool(re.search(r"^\s*\{.*\}\s*$", s))

    if not summary_text or looks_like_dict_dump(summary_text):
        summary_text = build_deterministic_summary_text(ok, issues, counts)

    if structured is None:
        structured = {}

    return summary_text, structured

# =========================
# Markdown formatting helper (NEW)
# =========================
def _to_markdown(out_doc: Dict[str, Any]) -> str:
    """
    Convert the output JSON document into a concise Markdown card
    for non-technical viewers in the ADK web chat.
    """
    status_emoji = "✅" if out_doc.get("ok") else "❌"
    title = f"{status_emoji} **Validation Result** — `{out_doc.get('record_hint', '<unknown>')}`"
    path_line = f"**Input file:** `{out_doc.get('input_file')}`"
    counts = out_doc.get("counts", {})
    counts_md = (
        f"- Schema issues: **{counts.get('schema_issues', 0)}**\n"
        f"- Null issues: **{counts.get('null_issues', 0)}**\n"
        f"- Timestamp issues: **{counts.get('timestamp_issues', 0)}**\n"
        f"- Total issues: **{counts.get('total', 0)}**"
    )

    # Top issues list (limit to 5 for readability)
    issues = out_doc.get("issues", []) or []
    if issues:
        issue_lines = []
        for i in issues[:5]:
            cat = i.get("category", "issue")
            field = i.get("field_path", "")
            sev = i.get("severity", "")
            detail = i.get("detail", "")
            # detail can be dict or str
            if isinstance(detail, dict):
                detail_str = "; ".join(f"{k}: {v}" for k, v in detail.items())
            else:
                detail_str = str(detail)
            issue_lines.append(f"- **{cat}** ({sev}) — `{field}`: {detail_str}")
        issues_md = "\n".join(issue_lines)
    else:
        issues_md = "- No issues found."

    # LLM summary text
    llm = out_doc.get("llm", {})
    llm_summary = llm.get("summary_text", "") or "Summary not available."
    llm_summary_md = llm_summary.strip()

    # LLM structured remediation
    llm_struct = llm.get("structured", {}) or {}
    plan = llm_struct.get("remediation_plan", []) or []
    if plan:
        plan_lines = []
        for step in plan[:5]:
            pr = step.get("priority", "medium")
            st = step.get("step", "")
            ex = step.get("example", "")
            bullet = f"- **{pr.capitalize()}** — {st}"
            if ex:
                bullet += f" _(e.g., {ex})_"
            plan_lines.append(bullet)
        plan_md = "\n".join(plan_lines)
    else:
        plan_md = "- Remediation steps will be provided when applicable."

    # Timestamp metrics (brief)
    tm = out_doc.get("timestamp_metrics", {}) or {}
    lags = tm.get("lags_sec", {}) or {}
    availability = tm.get("availability", {}) or {}
    lag_md = (
        f"- Event → Publish: **{lags.get('event_to_publish', '—')}s**\n"
        f"- Publish → Validate: **{lags.get('publish_to_validate', '—')}s**\n"
        f"- Validate → Commit: **{lags.get('validate_to_commit', '—')}s**"
    )
    avail_md = ", ".join(k for k, v in availability.items() if v) or "—"

    md = (
        f"{title}\n\n"
        f"{path_line}\n\n"
        f"### Status\n"
        f"- Overall: **{'PASS' if out_doc.get('ok') else 'FAIL'}**\n\n"
        f"### Issue Counts\n{counts_md}\n\n"
        f"### Top Findings\n{issues_md}\n\n"
        f"### LLM Explanation\n{llm_summary_md}\n\n"
        f"### Suggested Remediations\n{plan_md}\n\n"
        f"### Timing Metrics\n{lag_md}\n\n"
        f"**Timestamp availability:** {avail_md}\n"
    )
    return md

# =========================
# Batch Validation Agent (posts Markdown to chat)
# =========================
class BatchValidationAgent(BaseAgent):
    name: str = "batch_validation_runner"
    description: str = "Validates all JSONs, explains via Gemini, writes outputs, and posts Markdown summaries to chat."

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state

        # Path checks
        if not SCHEMA_PATH.is_file():
            msg = f"Schema file not found: {SCHEMA_PATH}"
            yield Event(
                author=self.name,
                content=types.Content(parts=[types.Part(text=f"**Error:** {msg}")]),
                actions=EventActions(state_delta={"batch_summary": {"ok": False, "detail": msg}}, skip_summarization=True),
            )
            return
        if not INPUT_DIR.is_dir():
            msg = f"Input directory not found: {INPUT_DIR}"
            yield Event(
                author=self.name,
                content=types.Content(parts=[types.Part(text=f"**Error:** {msg}")]),
                actions=EventActions(state_delta={"batch_summary": {"ok": False, "detail": msg}}, skip_summarization=True),
            )
            return

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Load schema once
        try:
            schema = load_json_local(SCHEMA_PATH)
        except Exception as e:
            msg = f"Failed to load schema: {e}"
            yield Event(
                author=self.name,
                content=types.Content(parts=[types.Part(text=f"**Error:** {msg}")]),
                actions=EventActions(state_delta={"batch_summary": {"ok": False, "detail": msg}}, skip_summarization=True),
            )
            return

        # Discover inputs
        candidates: List[Path] = [p for p in INPUT_DIR.iterdir() if p.is_file() and looks_like_json_file(p)]
        if not candidates:
            msg = f"No JSON files found in input: {INPUT_DIR}"
            yield Event(
                author=self.name,
                content=types.Content(parts=[types.Part(text=msg)]),
                actions=EventActions(state_delta={"batch_summary": {"ok": True, "processed": 0, "files": [], "detail": "No JSON files found in input."}}, skip_summarization=True),
            )
            return

        # Overrides
        critical_paths: List[str] = state.get("critical_paths") or DEFAULT_CRITICAL_PATHS
        tolerances: Dict[str, float] = state.get("tolerances") or DEFAULT_TOLERANCES

        aggregate_counts = {"schema_issues": 0, "null_issues": 0, "timestamp_issues": 0, "total": 0}
        per_file_status: List[Dict[str, Any]] = []
        total_processed = 0

        for input_path in sorted(candidates):
            total_processed += 1

            # Safe load
            try:
                record = load_json_local(input_path)
                if not isinstance(record, dict):
                    raise ValueError("Top-level JSON must be an object.")
            except Exception as exc:
                issues = [{
                    "category": "input_parse_error",
                    "field_path": "",
                    "detail": f"Failed to read/parse JSON: {exc}",
                    "validator": "json",
                    "severity": "high",
                }]
                counts = {"schema_issues": 0, "null_issues": 0, "timestamp_issues": 0, "total": len(issues)}
                ok = False
                record_hint = "<unreadable>"
                ts_metrics: Dict[str, Any] = {}

                validation_summary = {
                    "counts": counts,
                    "timestamp_metrics": ts_metrics,
                    "record_hint": record_hint,
                    "selected_file": str(input_path),
                }
                llm_summary_text, llm_structured = invoke_gemini_explanation({"ok": ok, "issues": issues, "summary": validation_summary})

                out_doc = _build_output_doc(
                    input_path=input_path,
                    record_hint=record_hint,
                    counts=counts,
                    timestamp_metrics=ts_metrics,
                    issues=issues,
                    ok=ok,
                    llm_summary_text=llm_summary_text,
                    llm_structured=llm_structured,
                )
            else:
                # Deterministic validations
                try:
                    schema_issues = iter_contract_issues_full(record, schema)
                except Exception as e:
                    schema_issues = [{
                        "category": "schema_validation_error",
                        "field_path": "",
                        "detail": str(e),
                        "validator": "jsonschema",
                        "severity": "high",
                    }]

                null_issues = collect_null_policy_issues(record, critical_paths)
                ts_issues, ts_metrics = check_pipeline_timestamps(record, tolerances)

                issues: List[Dict[str, Any]] = schema_issues + null_issues + ts_issues
                counts = {
                    "schema_issues": len(schema_issues),
                    "null_issues": len(null_issues),
                    "timestamp_issues": len(ts_issues),
                    "total": len(issues),
                }
                ok = len(issues) == 0
                record_hint = record.get("wallet_id") or record.get("customer_id") or "<unknown>"

                validation_summary = {
                    "counts": counts,
                    "timestamp_metrics": ts_metrics,
                    "record_hint": record_hint,
                    "selected_file": str(input_path),
                }
                llm_summary_text, llm_structured = invoke_gemini_explanation({"ok": ok, "issues": issues, "summary": validation_summary})

                out_doc = _build_output_doc(
                    input_path=input_path,
                    record_hint=record_hint,
                    counts=counts,
                    timestamp_metrics=ts_metrics,
                    issues=issues,
                    ok=ok,
                    llm_summary_text=llm_summary_text,
                    llm_structured=llm_structured,
                )

                # Aggregates
                for k in aggregate_counts.keys():
                    aggregate_counts[k] += counts.get(k, 0)

            # Write output per file
            out_path = OUTPUT_DIR / f"{input_path.stem}.validation.json"
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(out_doc, f, indent=2, ensure_ascii=False)
                per_file_status.append({"file": str(input_path), "output": str(out_path), "ok": out_doc["ok"], "counts": out_doc["counts"]})
            except Exception as write_exc:
                per_file_status.append({"file": str(input_path), "output": str(out_path), "ok": False, "error": f"Failed to write output: {write_exc}"})

            # === SHOW per-file output in ADK chat as Markdown ===
            markdown = _to_markdown(out_doc)
            yield Event(
                author=self.name,
                content=types.Content(parts=[types.Part(text=markdown)]),
                actions=EventActions(skip_summarization=True),  # render our Markdown as-is
            )

        # Final batch summary (state + chat)
        batch_summary = {
            "ok": True,
            "processed": total_processed,
            "aggregate_counts": aggregate_counts,
            "files": per_file_status,
            "output_dir": str(OUTPUT_DIR),
        }
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"batch_summary": batch_summary}, skip_summarization=True),
        )
        summary_md = (
            f"## Batch Completed\n"
            f"- Processed: **{total_processed}** file(s)\n"
            f"- Output folder: `{OUTPUT_DIR}`\n"
            f"- Aggregate counts:\n"
            f"  - Schema: **{aggregate_counts['schema_issues']}**\n"
            f"  - Null: **{aggregate_counts['null_issues']}**\n"
            f"  - Timestamp: **{aggregate_counts['timestamp_issues']}**\n"
            f"  - Total: **{aggregate_counts['total']}**\n"
        )
        yield Event(
            author=self.name,
            content=types.Content(parts=[types.Part(text=summary_md)]),
            actions=EventActions(skip_summarization=True),
        )
        return

# =========================
# Root workflow (Batch-first)
# =========================
root_agent = SequentialAgent(
    name="wallet_contract_batch_validation_workflow",
    description="Batch validate all inputs, explain with Gemini, write outputs, and post Markdown summaries to chat (prompt-independent).",
    sub_agents=[BatchValidationAgent()],
)

# Optional CLI test
if __name__ == "__main__":
    class _DummySession:
        state: Dict[str, Any] = {}
    class _DummyContext:
        session = _DummySession()
    import asyncio
    async def _run():
        ctx = _DummyContext()
        agent = BatchValidationAgent()
        async for _ in agent._run_async_impl(ctx):
            pass
        summary = ctx.session.state.get("batch_summary")
        print(json.dumps(summary, indent=2))
    asyncio.run(_run())
