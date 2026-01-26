
"""
Retention Agent
================
Handles customer retention when they attempt to cancel policies.
Presents offers and incentives to keep customers.
"""

from google.adk.agents.llm_agent import Agent
from google.adk.tools import FunctionTool

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.retention_tools import (
    present_retention_offers,
    apply_retention_offer,
    get_cancellation_reasons,
    process_cancellation_with_reason,
    calculate_loyalty_score
)


def present_offers_tool(customer_id: str, policy_id: str) -> dict:
    """
    Present retention offers to a customer considering cancellation.
    
    Args:
        customer_id: The customer's ID
        policy_id: The policy they want to cancel
        
    Returns:
        Formatted retention offers
    """
    offers = present_retention_offers(customer_id, policy_id)
    return {"offers": offers}


def apply_offer_tool(customer_id: str, policy_id: str, offer_id: str) -> dict:
    """
    Apply a retention offer to a customer's policy.
    
    Args:
        customer_id: The customer's ID
        policy_id: The policy ID
        offer_id: The offer ID they want to accept
        
    Returns:
        Confirmation of applied offer with new terms
    """
    success, message = apply_retention_offer(customer_id, policy_id, offer_id)
    return {"success": success, "message": message}


def get_cancellation_reasons_tool() -> dict:
    """
    Get the list of cancellation reasons to present to the customer.
    
    Returns:
        List of reason options
    """
    reasons = get_cancellation_reasons()
    return {"reasons": reasons}


def process_cancellation_tool(policy_id: str, reason: str) -> dict:
    """
    Process the final cancellation after customer declines all offers.
    
    Args:
        policy_id: The policy to cancel
        reason: The cancellation reason
        
    Returns:
        Cancellation confirmation
    """
    message = process_cancellation_with_reason(policy_id, reason)
    return {"message": message}


def get_customer_value_tool(customer_id: str) -> dict:
    """
    Get customer loyalty information for internal reference.
    
    Args:
        customer_id: The customer's ID
        
    Returns:
        Loyalty score and tier information
    """
    score = calculate_loyalty_score(customer_id)
    return {
        "tier": score["tier"].upper(),
        "score": score["score"],
        "tenure_years": score["tenure_years"],
        "active_policies": score["active_policies"],
        "monthly_premium": f"£{score['monthly_premium']:.2f}"
    }


# Create the agent
retention_agent = Agent(
    model='gemini-2.5-flash',
    name='retention_agent',
    description='Retains customers who want to cancel by presenting personalized offers and incentives.',
    instruction="""You are the Retention Agent for Aviva Insurance.

Your mission is to retain customers who are considering cancellation.

Retention process:
1. Express understanding and empathy for their situation
2. Check their customer value/loyalty tier (internally)
3. Present personalized retention offers
4. If they accept an offer, apply it immediately
5. If they decline all offers, ask for their reason and process the cancellation

Available offers typically include:
- Discount offers (10-30% off premium)
- Premium freeze (lock current rate)
- Enhanced coverage bonuses
- Loyalty rewards

Guidelines:
- NEVER pressure customers - respect their decision
- Lead with empathy: "I understand, and I want to make sure we explore all options"
- Present offers as genuine appreciation for their business
- For high-value customers (Gold/Platinum tier), offer the best deals
- If they insist on cancelling, process it gracefully
- Always end positively, leaving the door open for return
- Use British English spelling and polite phrasing.

Remember: A customer who leaves feeling respected may come back. 
A customer who feels pressured never will.""",
    tools=[
        FunctionTool(func=present_offers_tool),
        FunctionTool(func=apply_offer_tool),
        FunctionTool(func=get_cancellation_reasons_tool),
        FunctionTool(func=process_cancellation_tool),
        FunctionTool(func=get_customer_value_tool)
    ]
)
