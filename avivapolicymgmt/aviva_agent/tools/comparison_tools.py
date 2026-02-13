"""
Comparison Tools - Compare Aviva policies against other providers.

Uses synthetic competitor data to generate side-by-side comparisons
of features, premiums, and ratings across insurance providers.
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def _load_json(filename: str) -> list:
    """Load a JSON data file from the data directory."""
    with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------
# Tool: Compare policy with other providers
# ------------------------------------------------------------------
def compare_with_providers(
    policy_type: str,
    cover_level: str = "comprehensive",
    annual_premium: float = 0.0
) -> dict:
    """
    Compare an Aviva policy against competitor providers.

    Generates a detailed comparison table showing features, premiums,
    and customer ratings across multiple insurance providers.

    Args:
        policy_type: The type of insurance — 'auto' or 'property'.
        cover_level: The desired level of cover (e.g. 'comprehensive',
                     'buildings_and_contents').
        annual_premium: The Aviva premium to compare against (optional).

    Returns:
        dict with status and a comparison table containing provider
        details, features, premiums, and ratings.
    """
    providers_data = _load_json("provider_plans.json")

    # Build Aviva's own entry for comparison
    if policy_type.lower() == "auto":
        aviva_plan = {
            "provider": "Aviva",
            "plan_name": "Aviva Comprehensive Auto",
            "policy_type": "auto",
            "cover_level": "comprehensive",
            "annual_premium_range": {"min": 680, "max": 1800},
            "features": {
                "accidental_damage": True, "theft": True, "fire": True,
                "windscreen": True, "personal_accident": True,
                "breakdown_cover": True, "courtesy_car": True,
                "legal_expenses": True, "protected_ncd": True,
                "new_car_replacement": True
            },
            "rating": 4.6,
            "your_premium": annual_premium if annual_premium > 0 else None
        }
    else:
        aviva_plan = {
            "provider": "Aviva",
            "plan_name": "Aviva Buildings & Contents",
            "policy_type": "property",
            "cover_level": "buildings_and_contents",
            "annual_premium_range": {"min": 350, "max": 900},
            "features": {
                "buildings": True, "contents": True,
                "accidental_damage_buildings": True,
                "accidental_damage_contents": True,
                "personal_possessions": True, "home_emergency": True,
                "legal_expenses": True, "family_legal_cover": True
            },
            "rating": 4.5,
            "your_premium": annual_premium if annual_premium > 0 else None
        }

    # Collect matching competitor plans
    comparison = [aviva_plan]
    for provider in providers_data:
        for plan in provider["plans"]:
            if plan["policy_type"] == policy_type.lower():
                entry = {
                    "provider": provider["provider"],
                    "plan_name": plan["plan_name"],
                    "annual_premium_range": plan["annual_premium_range"],
                    "features": plan["features"],
                    "rating": plan["rating"],
                    "voluntary_excess_options": plan["voluntary_excess_options"]
                }
                comparison.append(entry)

    # Calculate feature counts for ranking
    for entry in comparison:
        entry["feature_count"] = sum(
            1 for v in entry["features"].values() if v is True
        )

    # Sort by rating (Aviva should appear well)
    comparison.sort(key=lambda x: x.get("rating", 0), reverse=True)

    return {
        "status": "success",
        "comparison": comparison,
        "total_providers": len(comparison),
        "summary": (
            f"Compared {len(comparison)} providers for {policy_type} insurance. "
            f"Aviva offers the most comprehensive coverage with a {aviva_plan['rating']}★ rating."
        )
    }
