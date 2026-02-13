"""
Suggestion Tools - Life-event and cross-sell recommendation engine.

Provides contextual insurance suggestions based on customer life events
(e.g. child turning 18, getting married, buying a house) and identifies
coverage gaps for cross-selling opportunities.
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def _load_json(filename: str) -> list:
    """Load a JSON data file from the data directory."""
    with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------
# Life-event suggestion mapping
# ------------------------------------------------------------------
LIFE_EVENT_SUGGESTIONS = {
    "child_turning_18": {
        "auto": [
            "Consider adding your child as a named driver — this can be cheaper than a separate policy.",
            "Young driver telematics policies are available for first-time drivers at competitive rates.",
            "Starting with a smaller engine car (under 1.2L) could significantly reduce premiums for new drivers."
        ],
        "property": [
            "If your child is heading to university, consider updating your contents cover for items taken to halls.",
            "Personal possessions cover can protect laptops and phones outside the home."
        ]
    },
    "getting_married": {
        "auto": [
            "Married couples often receive lower premiums — update your marital status to potentially save.",
            "Consider a joint policy if your spouse also drives the same vehicle.",
            "Multi-car policies offer significant discounts when insuring two vehicles together."
        ],
        "property": [
            "Combine your home insurance into a joint policy for better rates.",
            "Update your contents value if you're merging households.",
            "Wedding gifts increase your contents value — consider a temporary uplift in cover."
        ]
    },
    "buying_house": {
        "property": [
            "You'll need buildings insurance for your mortgage — we can bundle buildings and contents at a discount.",
            "New-build homes often qualify for lower premiums due to modern security features.",
            "Consider home emergency cover for peace of mind in your new property."
        ],
        "auto": [
            "Your new postcode may affect your car insurance premium — updating it now could save you money.",
            "If you now have a garage, changing your parking location could reduce your premium."
        ]
    },
    "moving_house": {
        "property": [
            "Your new area's risk profile may change your premium — let's recalculate.",
            "Check that your rebuild value is accurate for the new property.",
            "Consider flood risk cover if your new area has different exposure."
        ],
        "auto": [
            "Updating your address is required by law — and a lower-risk area could reduce premiums.",
            "If your commute has changed, updating your annual mileage could save money."
        ]
    },
    "new_car": {
        "auto": [
            "We can transfer your existing no-claims discount to the new vehicle.",
            "Comprehensive cover is recommended for newer vehicles — consider upgrading.",
            "GAP insurance protects against depreciation if the car is written off in the first few years."
        ]
    },
    "commuting_new_job": {
        "auto": [
            "If you're now commuting, make sure your usage type includes 'commuting' cover.",
            "Business use cover is needed if you drive to multiple work locations.",
            "Consider updating your annual mileage estimate based on your new commute."
        ]
    },
    "retirement": {
        "auto": [
            "Reduced mileage in retirement could lower your premium significantly.",
            "Consider switching from commuting cover to social-only for savings.",
            "You may now qualify for a mature driver discount."
        ],
        "property": [
            "Being home more often can reduce your theft risk rating.",
            "Consider reducing your contents cover if you're downsizing."
        ]
    }
}


# ------------------------------------------------------------------
# Tool: Get suggestions based on life events
# ------------------------------------------------------------------
def get_suggestions(customer_id: str, life_event: str = "") -> dict:
    """
    Get personalised insurance suggestions based on customer life events.

    Analyses the customer's current situation and provides relevant
    recommendations for policy adjustments or new coverage.

    Args:
        customer_id: The customer identifier (e.g. 'CUST-001').
        life_event: Optional specific life event to get suggestions for.
                    Options: 'child_turning_18', 'getting_married',
                    'buying_house', 'moving_house', 'new_car',
                    'commuting_new_job', 'retirement'.
                    If empty, uses the customer's recorded life events.

    Returns:
        dict with status and personalised suggestions.
    """
    customers = _load_json("customers.json")
    customer = next((c for c in customers if c["customer_id"] == customer_id), None)

    if not customer:
        return {
            "status": "error",
            "error_message": f"Customer '{customer_id}' not found."
        }

    # Determine which life events to use
    events = [life_event] if life_event else customer.get("life_events", [])

    if not events:
        return {
            "status": "no_events",
            "message": (
                f"No specific life events recorded for {customer['first_name']}. "
                "Would you like to tell us about any changes in your life so we can suggest the best options?"
            )
        }

    # Gather suggestions
    all_suggestions = []
    for event in events:
        if event in LIFE_EVENT_SUGGESTIONS:
            event_tips = LIFE_EVENT_SUGGESTIONS[event]
            for category, tips in event_tips.items():
                for tip in tips:
                    all_suggestions.append({
                        "life_event": event.replace("_", " ").title(),
                        "category": category,
                        "suggestion": tip
                    })

    if not all_suggestions:
        return {
            "status": "no_suggestions",
            "message": "No specific suggestions available for the given life events."
        }

    return {
        "status": "success",
        "customer_name": f"{customer['first_name']} {customer['last_name']}",
        "suggestions": all_suggestions,
        "total_suggestions": len(all_suggestions)
    }


# ------------------------------------------------------------------
# Tool: Get cross-sell suggestions based on coverage gaps
# ------------------------------------------------------------------
def get_cross_sell_suggestions(customer_id: str) -> dict:
    """
    Identify coverage gaps and suggest additional policies or add-ons.

    Analyses the customer's existing policies and recommends areas
    where additional coverage would be beneficial.

    Args:
        customer_id: The customer identifier (e.g. 'CUST-001').

    Returns:
        dict with status and cross-sell recommendations.
    """
    policies = _load_json("policies.json")
    customer_policies = [p for p in policies if p["customer_id"] == customer_id and p["status"] == "active"]

    has_auto = any(p["policy_type"] == "auto" for p in customer_policies)
    has_property = any(p["policy_type"] == "property" for p in customer_policies)

    suggestions = []

    # Suggest missing policy types
    if has_auto and not has_property:
        suggestions.append({
            "type": "new_policy",
            "category": "property",
            "suggestion": "You have car insurance but no home insurance with us. Bundle your home and car cover for up to 15% savings!",
            "priority": "high"
        })

    if has_property and not has_auto:
        suggestions.append({
            "type": "new_policy",
            "category": "auto",
            "suggestion": "You have home insurance but no car insurance with us. Multi-policy customers enjoy exclusive discounts!",
            "priority": "high"
        })

    # Check for add-on opportunities within existing policies
    coverages = _load_json("policy_coverages.json")
    for policy in customer_policies:
        pol_coverages = [c for c in coverages if c["policy_id"] == policy["policy_id"]]
        not_included = [c for c in pol_coverages if not c["included"]]

        for missing in not_included:
            cov_name = missing["coverage_type"].replace("_", " ").title()
            suggestions.append({
                "type": "add_on",
                "policy_id": policy["policy_id"],
                "category": policy["policy_type"],
                "suggestion": f"Consider adding {cov_name} to your {policy['policy_type']} policy for extra peace of mind.",
                "priority": "medium"
            })

    if not suggestions:
        suggestions.append({
            "type": "info",
            "suggestion": "Your coverage looks comprehensive! No additional recommendations at this time.",
            "priority": "low"
        })

    return {
        "status": "success",
        "suggestions": suggestions,
        "total_suggestions": len(suggestions)
    }
