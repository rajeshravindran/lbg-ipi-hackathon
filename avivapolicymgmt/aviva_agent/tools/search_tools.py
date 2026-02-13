"""
Search Tools - Search and filter policies.

Provides advanced search capabilities across policies, customers, and claims.
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def _load_json(filename: str) -> list:
    """Load a JSON data file from the data directory."""
    with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------
# Tool: Search policies by various criteria
# ------------------------------------------------------------------
def search_policies(
    customer_id: str = "",
    policy_type: str = "",
    status: str = "",
    cover_level: str = ""
) -> dict:
    """
    Search and filter insurance policies by multiple criteria.

    All parameters are optional. If none are provided, returns all policies.
    Multiple criteria are combined with AND logic.

    Args:
        customer_id: Filter by customer ID (e.g. 'CUST-001').
        policy_type: Filter by type — 'auto' or 'property'.
        status: Filter by status — 'active', 'cancelled', 'expired'.
        cover_level: Filter by cover level — 'comprehensive',
                     'third_party_fire_theft', 'buildings_and_contents'.

    Returns:
        dict with status, matching policies, and total count.
    """
    policies = _load_json("policies.json")
    results = policies

    # Apply filters
    if customer_id:
        results = [p for p in results if p["customer_id"] == customer_id]
    if policy_type:
        results = [p for p in results if p["policy_type"] == policy_type.lower()]
    if status:
        results = [p for p in results if p["status"] == status.lower()]
    if cover_level:
        results = [p for p in results if p["cover_level"] == cover_level.lower()]

    # Enrich with asset names
    vehicles = _load_json("vehicles.json")
    properties = _load_json("properties.json")

    enriched = []
    for pol in results:
        summary = {
            "policy_id": pol["policy_id"],
            "policy_type": pol["policy_type"],
            "status": pol["status"],
            "annual_premium": pol["annual_premium"],
            "end_date": pol["end_date"]
        }
        if pol["policy_type"] == "auto" and "vehicle_id" in pol:
            veh = next((v for v in vehicles if v["vehicle_id"] == pol["vehicle_id"]), None)
            if veh:
                summary["asset"] = f"{veh['year']} {veh['make']} {veh['model']}"
        elif pol["policy_type"] == "property" and "property_id" in pol:
            prop = next((p for p in properties if p["property_id"] == pol["property_id"]), None)
            if prop:
                summary["asset"] = f"{prop['property_type']} at {prop['address']['city']}"
        enriched.append(summary)

    if not enriched:
        return {
            "status": "no_results",
            "message": "No policies match the given criteria."
        }

    return {
        "status": "success",
        "policies": enriched,
        "total_count": len(enriched)
    }


# ------------------------------------------------------------------
# Tool: Search claims for a customer
# ------------------------------------------------------------------
def search_claims(customer_id: str = "", policy_id: str = "") -> dict:
    """
    Search for insurance claims by customer or policy.

    Args:
        customer_id: Filter claims by customer ID.
        policy_id: Filter claims by policy ID.

    Returns:
        dict with status and list of matching claims.
    """
    claims = _load_json("claims.json")
    results = claims

    if customer_id:
        results = [c for c in results if c["customer_id"] == customer_id]
    if policy_id:
        results = [c for c in results if c["policy_id"] == policy_id]

    if not results:
        return {
            "status": "no_results",
            "message": "No claims found for the given criteria."
        }

    return {
        "status": "success",
        "claims": results,
        "total_count": len(results)
    }
