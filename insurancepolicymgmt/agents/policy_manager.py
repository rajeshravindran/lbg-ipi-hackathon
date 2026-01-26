"""
Policy Manager Agent
=====================
Handles all policy-related operations including listing, viewing,
updating, renewing, and cancelling policies.
"""

from google.adk.agents.llm_agent import Agent
from google.adk.tools import FunctionTool

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.policy_tools import (
    list_customer_policies,
    renew_policy,
    cancel_policy,
    modify_coverage
)
from tools.data_tools import get_policy_by_id, get_policy_details


def list_policies_tool(customer_id: str, include_cancelled: bool = False) -> dict:
    """
    List all policies for a customer.
    
    Args:
        customer_id: The customer's ID
        include_cancelled: Whether to include cancelled policies
        
    Returns:
        Formatted list of customer's policies
    """
    policies_list = list_customer_policies(customer_id, include_cancelled)
    return {"policies": policies_list}


def get_policy_details_tool(policy_id: str) -> dict:
    """
    Get detailed information about a specific policy.
    
    Args:
        policy_id: The policy ID (e.g., POL001)
        
    Returns:
        Complete policy details including type-specific information
    """
    policy = get_policy_by_id(policy_id)
    if not policy:
        return {"error": f"Policy {policy_id} not found"}
    
    details = get_policy_details(policy_id, policy["policy_type"])
    
    result = {
        "policy_id": policy["id"],
        "type": policy["policy_type"],
        "status": policy["status"],
        "coverage": f"£{policy['coverage_amount']:,}",
        "monthly_premium": f"£{policy['monthly_premium']:.2f}",
        "start_date": policy["start_date"],
        "end_date": policy["end_date"]
    }
    
    if details:
        result["details"] = details
    
    return result


def renew_policy_tool(policy_id: str, years: int = 1) -> dict:
    """
    Renew an existing policy.
    
    Args:
        policy_id: The policy ID to renew
        years: Number of years to renew for (default: 1)
        
    Returns:
        Renewal confirmation or error message
    """
    success, message = renew_policy(policy_id, years)
    return {"success": success, "message": message}


def modify_coverage_tool(policy_id: str, new_coverage_amount: float) -> dict:
    """
    Modify the coverage amount of an existing policy.
    This will also adjust the premium accordingly.
    
    Args:
        policy_id: The policy ID to modify
        new_coverage_amount: New coverage amount in dollars
        
    Returns:
        Modification result with new premium information
    """
    success, message = modify_coverage(policy_id, new_coverage_amount)
    return {"success": success, "message": message}


def initiate_cancellation_tool(policy_id: str) -> dict:
    """
    Start the cancellation process for a policy.
    Note: This should trigger the retention flow before actually cancelling.
    
    Args:
        policy_id: The policy ID to cancel
        
    Returns:
        Indication that retention offers should be presented
    """
    policy = get_policy_by_id(policy_id)
    if not policy:
        return {"error": f"Policy {policy_id} not found"}
    
    return {
        "action": "route_to_retention",
        "policy_id": policy_id,
        "message": "Before processing the cancellation, let me check if we have any special offers for you."
    }


# Create the agent
policy_manager_agent = Agent(
    model='gemini-2.5-flash',
    name='policy_manager_agent',
    description='Manages insurance policies - list, view details, renew, modify coverage, or initiate cancellation.',
    instruction="""You are the Policy Manager Agent for Aviva Insurance.

Your responsibilities:
1. List customer policies when requested
2. Provide detailed information about specific policies
3. Process policy renewals
4. Handle coverage modifications (increase/decrease)
5. Initiate cancellation process (but route to retention agent first)

Important guidelines:
- Always confirm changes before processing them
- Explain the impact of changes (new premium, coverage, etc.)
- For cancellations, ALWAYS route to retention first - never process immediately
- Be helpful in explaining policy details in simple terms
- Maintain a professional and supportive tone
- Use British English spelling and currency (£) in all communications.

When a customer wants to cancel, express understanding but let them know you'll check for special offers first.""",
    tools=[
        FunctionTool(func=list_policies_tool),
        FunctionTool(func=get_policy_details_tool),
        FunctionTool(func=renew_policy_tool),
        FunctionTool(func=modify_coverage_tool),
        FunctionTool(func=initiate_cancellation_tool)
    ]
)
