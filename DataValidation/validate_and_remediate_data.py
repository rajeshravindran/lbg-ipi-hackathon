"""
validate_and_remediate_single_min.py

- Reads CSV from the same directory (expects: customers_with_address_id.csv).
- A row is INVALID if:
    (a) schema drift (missing/extra columns),
    (b) missing mandatory field(s) / unexpected nulls.
- ONLY remediation:
    * UK mobile normalization (E.164): +447#########
    * UK postcode formatting: OUTWARD + space + INWARD (e.g., SW1A 1AA)
- Writes ONE CSV with 'Comment' column: customers_validated_remediated.csv
"""

import re
import sys
import pandas as pd
from typing import List, Tuple

# Regular Expressions for remediation
UK_POSTCODE_RE = re.compile(r"^(GIR 0AA|[A-Z]{1,2}\d[A-Z\d]? \d[A-Z]{2})$")
UK_MOBILE_E164_RE = re.compile(r"^\+447\d{9}$")

# Mandatory fields per the agreed data contract
MANDATORY = {
    "customer_id", "first_name", "last_name", "dob", "nationality",
    "email", "phone", "source_channel", "consent_obtained",
    "created_at", "updated_at", "data_masked",
    # Address
    "address_type", "address_line1", "city", "postcode", "country",
    # ID proof
    "id_type", "id_value_masked", "issuing_country", "document_present"
}

# Expected columns (order not enforced)
EXPECTED_COLUMNS = [
    "customer_id","title","first_name","last_name","dob","gender",
    "nationality","email","phone","employment_status","annual_income_gbp",
    "source_channel","consent_obtained","pep_flag","created_at","updated_at","data_masked",
    "address_type","address_line1","address_line2","city","county","postcode","country",
    "raw_address","std_address","std_provider","std_status","classification",
    "geo_lat","geo_lon","is_primary",
    "id_type","id_value_masked","issuing_country","expiry_date","document_present",
    "name_on_document","dob_on_document","address_on_document","upload_channel"
]

# ------------------------
# Normalization helpers
# ------------------------
def normalize_uk_mobile(phone: str) -> str:
    """Normalize to +447######### if possible; otherwise return original."""
    if phone is None:
        return phone
    digits = re.sub(r"[^\d]", "", str(phone))
    if digits.startswith("0"):
        digits = "44" + digits[1:]
    elif digits.startswith("44"):
        pass
    elif digits.startswith("7"):
        digits = "44" + digits
    if digits.startswith("447") and len(digits) >= 12:
        candidate = "+" + digits[:12]
        return candidate if UK_MOBILE_E164_RE.match(candidate) else "+" + digits[:12]
    return phone

def normalize_uk_postcode(pc: str) -> str:
    """Uppercase and insert single space before inward code (last 3 chars)."""
    if pc is None:
        return pc
    cleaned = re.sub(r"[^A-Za-z0-9]", "", str(pc)).upper()
    if len(cleaned) < 5:
        return pc  # too short to safely normalize
    return cleaned[:-3] + " " + cleaned[-3:]

# ------------------------
# Schema drift check
# ------------------------
def check_schema_drift(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    extra = [c for c in df.columns if c not in EXPECTED_COLUMNS]
    return missing, extra

# ------------------------
# Row validation
# ------------------------
def validate_row(row: pd.Series) -> List[str]:
    """Return a list of issues for a row based ONLY on mandatory nulls (unexpected nulls)."""
    issues: List[str] = []
    for f in MANDATORY:
        v = row.get(f, None)
        if v is None or str(v).strip() == "":
            issues.append(f"{f}:mandatory_non_null")
    return issues

# ------------------------
# Pipeline: read -> schema check -> remediate -> row validate -> write output CSV file with Comment.
# ------------------------
def main():
    input_csv = "customers_with_address_id.csv"  
    output_csv = "customers_validated_remediated.csv"

    print(f"[INFO] Reading: {input_csv}")
    try:
        df = pd.read_csv(input_csv, dtype=str).fillna("")
    except FileNotFoundError:
        print(f"[ERROR] Could not find {input_csv} in the current directory.", file=sys.stderr)
        sys.exit(1)

    # Schema drift (dataset-level)
    missing, extra = check_schema_drift(df)
    schema_issue_fragments = []
    if missing:
        schema_issue_fragments.append(f"schema_drift:missing_columns={','.join(missing)}")
    if extra:
        schema_issue_fragments.append(f"schema_drift:extra_columns={','.join(extra)}")
    schema_issue_combined = "; ".join(schema_issue_fragments) if schema_issue_fragments else ""

    # Limited remediation
    print("[INFO] Applying limited remediation: UK mobile + postcode formatting")
    fixed_rows = []
    for idx in range(len(df)):
        row = df.iloc[idx].to_dict()
        row["phone"] = normalize_uk_mobile(row.get("phone"))
        row["postcode"] = normalize_uk_postcode(row.get("postcode"))
        fixed_rows.append(row)
    fixed_df = pd.DataFrame(fixed_rows, columns=df.columns)

    # Row validation (mandatory-only)
    print("[INFO] Validating rows (mandatory fields & unexpected nulls)")
    comments: List[str] = []
    for idx in range(len(fixed_df)):
        row_issues = validate_row(fixed_df.iloc[idx])
        issues = []
        if schema_issue_combined:
            issues.append(schema_issue_combined)
        issues.extend(row_issues)
        comments.append("VALID" if len(issues) == 0 else "INVALID - " + ", ".join(issues))

    fixed_df["Comment"] = comments
    fixed_df.to_csv(output_csv, index=False)
    print(f"[INFO] Wrote: {output_csv}")

if __name__ == "__main__":
    main()
