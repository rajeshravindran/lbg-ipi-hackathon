"""
Comparison Agent
=================
Compares insurance policies with competitor offerings.
Helps customers understand the value of their coverage.
"""

from google.adk.agents.llm_agent import Agent
from google.adk.tools import FunctionTool

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.comparison_tools import (
    compare_policies,
    compare_customer_policy,
    get_best_quote
)


def compare_policy_options_tool(policy_type: str, coverage_amount: float, 
                                 current_premium: float = None) -> dict:
    """
    Compare policy options across different insurance providers.
    
    Args:
        policy_type: Type of policy (life, property, vehicle)
        coverage_amount: Desired coverage amount in dollars
        current_premium: Optional current monthly premium for comparison
        
    Returns:
        Comparison table showing different providers and rates
    """
    comparison = compare_policies(policy_type, coverage_amount, current_premium)
    return {"comparison": comparison}


def compare_existing_policy_tool(policy_id: str) -> dict:
    """
    Compare a customer's existing policy with competitor offerings.
    Use this tool when a customer provides their policy ID like POL001, POL002, etc.
    
    Args:
        policy_id: The policy ID to compare (e.g., POL001, POL002)
        
    Returns:
        Comparison showing how the customer's policy stacks up against competitors
    """
    try:
        print(f"DEBUG: compare_existing_policy_tool START with {policy_id}")
        # Clean the policy ID - remove any extra spaces and convert to uppercase
        clean_id = policy_id.strip().upper()
        print(f"DEBUG: Cleaned ID: {clean_id}")
        
        comparison = compare_customer_policy(clean_id)
        print(f"DEBUG: Comparison result generated ({len(comparison)} chars)")
        print(f"DEBUG: START RESULT PREVIEW: {comparison[:50]}...")
        
        return {"comparison": comparison, "policy_id": clean_id, "status": "success"}
    except Exception as e:
        import traceback
        error_msg = f"Error comparing policy {policy_id}: {str(e)}\n{traceback.format_exc()}"
        print(f"DEBUG ERROR: {error_msg}")
        return {"error": error_msg, "status": "failed"}


def get_best_rate_tool(policy_type: str, coverage_amount: float) -> dict:
    """
    Get the best available rate for a policy type.
    
    Args:
        policy_type: Type of policy (life, property, vehicle)
        coverage_amount: Desired coverage amount in dollars
        
    Returns:
        Best available quote with competitor comparison
    """
    quote = get_best_quote(policy_type, coverage_amount)
    if quote:
        return {
            "our_rate": f"£{quote['our_premium']:.2f}/month",
            "best_competitor": quote['best_competitor'],
            "competitor_rate": f"£{quote['competitor_premium']:.2f}/month",
            "your_savings": f"£{quote['savings']:.2f}/month",
            "message": f"Our rate beats {quote['best_competitor']} by £{quote['savings']:.2f}/month!"
        }
    return {"error": "Unable to get quotes at this time"}


# Create the agent
comparison_agent = Agent(
    model='gemini-2.5-flash',
    name='comparison_agent',
    description='Compares insurance policies with competitor offerings to show value and savings.',
    instruction="""You are the Comparison Agent for Aviva Insurance.

Your role is to help customers understand how their coverage compares to the market.

## Tools Available

1. **compare_existing_policy_tool(policy_id)** - Use this when customer provides a policy ID (like POL001, POL002). This compares their existing policy with competitors.

2. **compare_policy_options_tool(policy_type, coverage_amount)** - Use this when customer wants to compare options for a NEW policy type.

3. **get_best_rate_tool(policy_type, coverage_amount)** - Use this to show the best available rate for a policy type.

## Key Flow

When a customer provides a policy ID:
1. Immediately call compare_existing_policy_tool with that policy ID
2. Present the comparison table to the customer
3. Highlight if their rate is competitive

Guidelines:
- Always present comparisons fairly and transparently
- Highlight our competitive advantages without disparaging competitors
- If you receive a policy ID, USE IT with compare_existing_policy_tool right away
- Present information in clear, professional tables
- Use British English spelling and tone throughout your responses.
- Ensure all currency is displayed in GBP (£).""",
    tools=[
        FunctionTool(func=compare_policy_options_tool),
        FunctionTool(func=compare_existing_policy_tool),
        FunctionTool(func=get_best_rate_tool)
    ]
)
