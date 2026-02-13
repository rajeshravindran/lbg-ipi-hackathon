"""
Policy Tools - CRUD operations for insurance policies.

Provides tools to retrieve, list, update, and cancel insurance policies.
All operations are backed by the JSON data files.
"""

import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def _load_json(filename: str) -> list:
    """Load a JSON data file from the data directory."""
    with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(filename: str, data: list) -> None:
    """Save data back to a JSON file in the data directory."""
    with open(os.path.join(DATA_DIR, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _log_audit(action: str, details: str, customer_id: str = "", policy_id: str = "") -> None:
    """Append an entry to the audit log."""
    log = _load_json("audit_log.json")
    log.append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "customer_id": customer_id,
        "policy_id": policy_id,
        "details": details
    })
    _save_json("audit_log.json", log)


# ------------------------------------------------------------------
# Tool: Get a single policy by ID
# ------------------------------------------------------------------
def get_policy(policy_id: str) -> dict:
    """
    Retrieve detailed information about a specific policy.

    Args:
        policy_id: The policy identifier (e.g. 'POL-AUTO-001').

    Returns:
        dict with status and full policy data including vehicle/property
        details and coverage information, or error_message if not found.
    """
    policies = _load_json("policies.json")
    policy = next((p for p in policies if p["policy_id"] == policy_id), None)

    if not policy:
        return {
            "status": "error",
            "error_message": f"Policy '{policy_id}' not found."
        }

    # Enrich with vehicle or property details
    result = {"status": "success", "policy": dict(policy)}

    if policy["policy_type"] == "auto" and "vehicle_id" in policy:
        vehicles = _load_json("vehicles.json")
        vehicle = next((v for v in vehicles if v["vehicle_id"] == policy["vehicle_id"]), None)
        if vehicle:
            result["vehicle"] = vehicle

    if policy["policy_type"] == "property" and "property_id" in policy:
        properties = _load_json("properties.json")
        prop = next((p for p in properties if p["property_id"] == policy["property_id"]), None)
        if prop:
            result["property"] = prop

    # Add coverage details
    coverages = _load_json("policy_coverages.json")
    result["coverages"] = [c for c in coverages if c["policy_id"] == policy_id]

    return result


# ------------------------------------------------------------------
# Tool: List all policies for a customer
# ------------------------------------------------------------------
def list_customer_policies(customer_id: str) -> dict:
    """
    List all insurance policies for a given customer.

    Args:
        customer_id: The customer identifier (e.g. 'CUST-001').

    Returns:
        dict with status and a list of policy summaries,
        or error_message if no policies found.
    """
    policies = _load_json("policies.json")
    customer_policies = [p for p in policies if p["customer_id"] == customer_id]

    if not customer_policies:
        return {
            "status": "error",
            "error_message": f"No policies found for customer '{customer_id}'."
        }

    # Enrich each policy with asset details
    vehicles = _load_json("vehicles.json")
    properties = _load_json("properties.json")

    summaries = []
    for pol in customer_policies:
        summary = {
            "policy_id": pol["policy_id"],
            "policy_type": pol["policy_type"],
            "status": pol["status"],
            "cover_level": pol["cover_level"],
            "annual_premium": pol["annual_premium"],
            "monthly_premium": pol["monthly_premium"],
            "start_date": pol["start_date"],
            "end_date": pol["end_date"],
            "auto_renew": pol["auto_renew"]
        }

        # Add vehicle or property info
        if pol["policy_type"] == "auto" and "vehicle_id" in pol:
            veh = next((v for v in vehicles if v["vehicle_id"] == pol["vehicle_id"]), None)
            if veh:
                summary["asset"] = f"{veh['year']} {veh['make']} {veh['model']} ({veh['vrn']})"
        elif pol["policy_type"] == "property" and "property_id" in pol:
            prop = next((p for p in properties if p["property_id"] == pol["property_id"]), None)
            if prop:
                summary["asset"] = f"{prop['property_type']} at {prop['address']['street']}, {prop['address']['city']}"

        summaries.append(summary)

    return {
        "status": "success",
        "policies": summaries,
        "total_count": len(summaries)
    }


# ------------------------------------------------------------------
# Tool: Update policy fields
# ------------------------------------------------------------------
def update_policy(policy_id: str, changes: str) -> dict:
    """
    Update specific fields on an existing policy.

    The changes should describe what needs updating in plain text.
    Supported changes: address, named drivers, excess, coverage level,
    usage type, auto-renew, annual mileage.

    Args:
        policy_id: The policy identifier.
        changes: JSON string describing changes, e.g.
                 '{"voluntary_excess": 500, "auto_renew": false}'

    Returns:
        dict with status and confirmation of applied changes.
    """
    policies = _load_json("policies.json")
    policy_index = next((i for i, p in enumerate(policies) if p["policy_id"] == policy_id), None)

    if policy_index is None:
        return {
            "status": "error",
            "error_message": f"Policy '{policy_id}' not found."
        }

    # Parse changes
    try:
        change_dict = json.loads(changes) if isinstance(changes, str) else changes
    except json.JSONDecodeError:
        return {
            "status": "error",
            "error_message": "Invalid changes format. Please provide valid JSON."
        }

    # Apply allowed field updates
    allowed_fields = [
        "voluntary_excess", "cover_level", "usage_type", "auto_renew",
        "named_drivers", "payment_method"
    ]
    applied = []
    for key, value in change_dict.items():
        if key in allowed_fields:
            policies[policy_index][key] = value
            applied.append(f"{key} → {value}")

    if not applied:
        return {
            "status": "error",
            "error_message": "No valid changes to apply. Allowed fields: " + ", ".join(allowed_fields)
        }

    _save_json("policies.json", policies)
    _log_audit("policy_update", f"Updated {', '.join(applied)}", 
               policies[policy_index]["customer_id"], policy_id)

    return {
        "status": "success",
        "message": f"Policy {policy_id} updated successfully.",
        "changes_applied": applied
    }


# ------------------------------------------------------------------
# Tool: Cancel a policy
# ------------------------------------------------------------------
def cancel_policy(policy_id: str, reason: str = "") -> dict:
    """
    Cancel an active insurance policy.

    Note: The system should attempt retention offers before calling this.

    Args:
        policy_id: The policy identifier to cancel.
        reason: The reason for cancellation provided by the customer.

    Returns:
        dict with status and cancellation confirmation.
    """
    policies = _load_json("policies.json")
    policy_index = next((i for i, p in enumerate(policies) if p["policy_id"] == policy_id), None)

    if policy_index is None:
        return {
            "status": "error",
            "error_message": f"Policy '{policy_id}' not found."
        }

    if policies[policy_index]["status"] != "active":
        return {
            "status": "error",
            "error_message": f"Policy '{policy_id}' is not currently active (status: {policies[policy_index]['status']})."
        }

    # Cancel the policy
    policies[policy_index]["status"] = "cancelled"
    policies[policy_index]["cancellation_date"] = datetime.now().strftime("%Y-%m-%d")
    policies[policy_index]["cancellation_reason"] = reason

    _save_json("policies.json", policies)
    _log_audit("policy_cancellation", f"Cancelled. Reason: {reason}",
               policies[policy_index]["customer_id"], policy_id)

    return {
        "status": "success",
        "message": f"Policy {policy_id} has been cancelled effective today. A confirmation email will be sent to your registered email address.",
        "refund_note": "Any pro-rata refund will be processed within 5-7 working days."
    }
