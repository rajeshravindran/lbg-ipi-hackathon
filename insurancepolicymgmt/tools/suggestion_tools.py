"""
Suggestion Tools Module
========================
Provides intelligent policy recommendations based on customer situations,
life events, and coverage gaps.
"""

from typing import Optional
from datetime import datetime, timedelta
from tools.data_tools import (
    get_customer_by_id, get_policies_by_customer,
    get_life_events_by_customer, load_json, save_json
)


def analyze_life_events(customer_id: str) -> list[dict]:
    """
    Analyze customer's life events and return upcoming events
    that may require new or modified coverage.
    
    Args:
        customer_id: ID of the customer
        
    Returns:
        List of relevant life events with suggestions
    """
    # Get unprocessed events
    events = get_life_events_by_customer(customer_id, processed=False)
    
    # Filter for upcoming events (within 90 days)
    today = datetime.now()
    upcoming = []
    
    for event in events:
        event_date = datetime.strptime(event["event_date"], "%Y-%m-%d")
        days_until = (event_date - today).days
        
        if -30 <= days_until <= 90:  # Include recent past events too
            event_copy = event.copy()
            event_copy["days_until"] = days_until
            event_copy["recommendations"] = _get_event_recommendations(event["event_type"])
            upcoming.append(event_copy)
    
    return upcoming


def _get_event_recommendations(event_type: str) -> list[dict]:
    """Get policy recommendations for a specific life event type."""
    recommendations = {
        "marriage": [
            {
                "policy_type": "life",
                "priority": "high",
                "reason": "Protect your spouse with life insurance coverage",
                "suggested_coverage": 500000
            },
            {
                "policy_type": "property",
                "priority": "medium",
                "reason": "Consider updating or getting homeowner's insurance if moving to a new home",
                "suggested_coverage": 350000
            }
        ],
        "child_turning_18": [
            {
                "policy_type": "vehicle",
                "priority": "high",
                "reason": "Your child may need their own auto insurance as a new driver",
                "suggested_coverage": 50000
            },
            {
                "policy_type": "life",
                "priority": "medium",
                "reason": "Consider a starter life insurance policy for your child",
                "suggested_coverage": 100000
            }
        ],
        "house_purchase": [
            {
                "policy_type": "property",
                "priority": "high",
                "reason": "Protect your new home with comprehensive homeowner's insurance",
                "suggested_coverage": 400000
            }
        ],
        "new_baby": [
            {
                "policy_type": "life",
                "priority": "high",
                "reason": "Increase life insurance to protect your growing family",
                "suggested_coverage": 750000
            }
        ],
        "retirement": [
            {
                "policy_type": "life",
                "priority": "medium",
                "reason": "Review life insurance needs - you may need less coverage or different type",
                "suggested_coverage": 250000
            },
            {
                "policy_type": "property",
                "priority": "low",
                "reason": "Consider adjusting property coverage if downsizing",
                "suggested_coverage": 300000
            }
        ]
    }
    
    return recommendations.get(event_type, [])


def get_coverage_gaps(customer_id: str) -> list[dict]:
    """
    Identify gaps in customer's current coverage.
    
    Args:
        customer_id: ID of the customer
        
    Returns:
        List of missing policy types with recommendations
    """
    policies = get_policies_by_customer(customer_id)
    active_policies = [p for p in policies if p["status"] == "active"]
    
    # Get policy types customer already has
    existing_types = {p["policy_type"] for p in active_policies}
    
    # Define standard coverage recommendation
    all_types = {
        "life": {
            "priority": "high",
            "reason": "Life insurance protects your family's financial future",
            "suggested_coverage": 500000
        },
        "property": {
            "priority": "medium",
            "reason": "Property insurance protects your home and belongings",
            "suggested_coverage": 350000
        },
        "vehicle": {
            "priority": "medium",
            "reason": "Vehicle insurance is required and protects against accidents",
            "suggested_coverage": 50000
        }
    }
    
    gaps = []
    for policy_type, details in all_types.items():
        if policy_type not in existing_types:
            gaps.append({
                "policy_type": policy_type,
                **details
            })
    
    return gaps


def get_recommendations(customer_id: str) -> str:
    """
    Get comprehensive policy recommendations for a customer.
    Combines life event analysis and coverage gap analysis.
    
    Args:
        customer_id: ID of the customer
        
    Returns:
        Formatted string with all recommendations
    """
    customer = get_customer_by_id(customer_id)
    if not customer:
        return "Customer not found."
    
    result = f"## Policy Recommendations for {customer['name']}\n\n"
    
    # Check for life events
    life_events = analyze_life_events(customer_id)
    
    if life_events:
        result += "### 🎯 Based on Your Life Events\n\n"
        
        for event in life_events:
            event_type_display = event["event_type"].replace("_", " ").title()
            
            if event["days_until"] > 0:
                timing = f"(in {event['days_until']} days)"
            elif event["days_until"] == 0:
                timing = "(today!)"
            else:
                timing = f"({abs(event['days_until'])} days ago)"
            
            result += f"**{event_type_display}** {timing}\n"
            
            for rec in event["recommendations"]:
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[rec["priority"]]
                result += f"- {priority_emoji} **{rec['policy_type'].title()} Insurance**: {rec['reason']}\n"
                result += f"  - Suggested coverage: £{rec['suggested_coverage']:,}\n"
            
            result += "\n"
    
    # Check for coverage gaps
    gaps = get_coverage_gaps(customer_id)
    
    if gaps:
        result += "### 📋 Coverage Gaps Identified\n\n"
        
        for gap in gaps:
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[gap["priority"]]
            result += f"{priority_emoji} **{gap['policy_type'].title()} Insurance**\n"
            result += f"- {gap['reason']}\n"
            result += f"- Recommended coverage: £{gap['suggested_coverage']:,}\n\n"
    
    # If no recommendations
    if not life_events and not gaps:
        result += "✅ **Great news!** Your current coverage appears comprehensive.\n\n"
        result += "We'll continue to monitor for any changes in your situation "
        result += "and notify you of relevant opportunities.\n"
    
    return result


def mark_event_processed(event_id: str) -> bool:
    """
    Mark a life event as processed after recommendations were made.
    
    Args:
        event_id: ID of the life event
        
    Returns:
        True if successful, False otherwise
    """
    events = load_json("life_events.json")
    
    for event in events:
        if event["id"] == event_id:
            event["processed"] = True
            save_json("life_events.json", events)
            return True
    
    return False


def suggest_for_new_customer(situation: str) -> str:
    """
    Suggest policies for a new customer based on their described situation.
    
    Args:
        situation: Description of customer's situation
        
    Returns:
        Formatted string with policy suggestions
    """
    result = "## Recommended Coverage for You\n\n"
    result += "Based on your situation, here are our recommendations:\n\n"
    
    suggestions = []
    
    # Parse situation keywords
    situation_lower = situation.lower()
    
    if any(word in situation_lower for word in ["family", "married", "spouse", "kids", "children"]):
        suggestions.append({
            "type": "life",
            "reason": "Protect your family's financial future",
            "coverage": 500000,
            "priority": "high"
        })
    
    if any(word in situation_lower for word in ["home", "house", "apartment", "property", "rent"]):
        suggestions.append({
            "type": "property",
            "reason": "Protect your home and belongings",
            "coverage": 350000,
            "priority": "high"
        })
    
    if any(word in situation_lower for word in ["car", "vehicle", "drive", "commute"]):
        suggestions.append({
            "type": "vehicle",
            "reason": "Required coverage for drivers",
            "coverage": 50000,
            "priority": "high"
        })
    
    # Default suggestion if nothing matched
    if not suggestions:
        suggestions = [
            {"type": "life", "reason": "Essential protection for everyone", "coverage": 250000, "priority": "medium"},
            {"type": "vehicle", "reason": "Protection for your transportation", "coverage": 30000, "priority": "medium"}
        ]
    
    for i, sug in enumerate(suggestions, 1):
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[sug["priority"]]
        result += f"### {i}. {sug['type'].title()} Insurance {priority_emoji}\n"
        result += f"- **Why**: {sug['reason']}\n"
        result += f"- **Suggested Coverage**: £{sug['coverage']:,}\n\n"
    
    result += "---\n"
    result += "Would you like to proceed with any of these options? "
    result += "I can provide detailed quotes and help you complete your purchase.\n"
    
    return result
