"""
Suggestion Agent
=================
Provides intelligent policy recommendations based on customer
situations, life events, and coverage gaps.
"""

from google.adk.agents.llm_agent import Agent
from google.adk.tools import FunctionTool

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.suggestion_tools import (
    get_recommendations,
    suggest_for_new_customer,
    analyze_life_events,
    get_coverage_gaps
)


def get_personalized_recommendations_tool(customer_id: str) -> dict:
    """
    Get personalized policy recommendations for an existing customer.
    Analyzes life events and coverage gaps.
    
    Args:
        customer_id: The customer's ID
        
    Returns:
        Formatted recommendations based on their situation
    """
    recommendations = get_recommendations(customer_id)
    return {"recommendations": recommendations}


def get_new_customer_suggestions_tool(situation_description: str) -> dict:
    """
    Get policy suggestions for a new customer based on their described situation.
    
    Args:
        situation_description: Description of the customer's situation
            (e.g., "married with two kids, own a home and two cars")
        
    Returns:
        Tailored policy suggestions
    """
    suggestions = suggest_for_new_customer(situation_description)
    return {"suggestions": suggestions}


def check_life_events_tool(customer_id: str) -> dict:
    """
    Check for upcoming life events that may require coverage changes.
    
    Args:
        customer_id: The customer's ID
        
    Returns:
        List of relevant life events with recommendations
    """
    events = analyze_life_events(customer_id)
    if events:
        return {
            "events_found": len(events),
            "events": [
                {
                    "type": e["event_type"].replace("_", " ").title(),
                    "date": e["event_date"],
                    "days_until": e["days_until"],
                    "recommendations": [r["policy_type"] for r in e["recommendations"]]
                }
                for e in events
            ]
        }
    return {"events_found": 0, "message": "No upcoming life events on record."}


def identify_coverage_gaps_tool(customer_id: str) -> dict:
    """
    Identify gaps in a customer's current coverage.
    
    Args:
        customer_id: The customer's ID
        
    Returns:
        List of missing policy types with recommendations
    """
    gaps = get_coverage_gaps(customer_id)
    if gaps:
        return {
            "gaps_found": len(gaps),
            "gaps": [
                {
                    "type": g["policy_type"],
                    "priority": g["priority"],
                    "reason": g["reason"],
                    "suggested_coverage": g["suggested_coverage"]
                }
                for g in gaps
            ]
        }
    return {"gaps_found": 0, "message": "Customer has comprehensive coverage across all policy types."}


# Create the agent
suggestion_agent = Agent(
    model='gemini-2.5-flash',
    name='suggestion_agent',
    description='Provides intelligent policy recommendations based on life events, coverage gaps, and customer situations.',
    instruction="""You are the Suggestion Agent for Aviva Insurance.

Your mission is to proactively help customers identify coverage they may need.

Key responsibilities:
1. Analyze life events (marriage, new baby, child turning 18, home purchase, retirement)
2. Identify coverage gaps in existing customers' portfolios
3. Provide tailored recommendations for new customers
4. Explain why specific coverage is important for their situation

Guidelines:
- Be proactive but not pushy
- Focus on customer protection, not just sales
- Explain the "why" behind each recommendation
- Prioritize recommendations by urgency (high/medium/low)
- For life events, be sensitive to the customer's situation
- Always tie recommendations to their specific circumstances

When discussing life events:
- Marriage → Suggest life insurance to protect spouse
- New baby → Suggest increased life insurance
- Child turning 18 → Suggest vehicle insurance for new drivers
- Home purchase → Suggest property insurance
- Retirement → Review and potentially adjust life insurance

Use British English spelling and tone in all recommendations.""",
    tools=[
        FunctionTool(func=get_personalized_recommendations_tool),
        FunctionTool(func=get_new_customer_suggestions_tool),
        FunctionTool(func=check_life_events_tool),
        FunctionTool(func=identify_coverage_gaps_tool)
    ]
)
