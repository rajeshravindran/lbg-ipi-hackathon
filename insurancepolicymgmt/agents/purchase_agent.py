"""
Purchase Agent
===============
Handles new policy purchases for both new and existing customers.
Guides customers through the quote and purchase process.
"""

from google.adk.agents.llm_agent import Agent
from google.adk.tools import FunctionTool

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.policy_tools import create_policy
from tools.comparison_tools import get_best_quote


def get_quote_tool(policy_type: str, coverage_amount: float) -> dict:
    """
    Get a quote for a new policy.
    
    Args:
        policy_type: Type of policy (life, property, vehicle)
        coverage_amount: Desired coverage amount in dollars
        
    Returns:
        Quote details including premium and comparison to competitors
    """
    quote = get_best_quote(policy_type, coverage_amount)
    if quote:
        return {
            "policy_type": policy_type.title(),
            "coverage_amount": f"£{coverage_amount:,}",
            "monthly_premium": f"£{quote['our_premium']:.2f}",
            "annual_premium": f"£{quote['our_premium'] * 12:,.2f}",
            "market_comparison": f"£{quote['savings']:.2f}/month less than {quote['best_competitor']}",
            "message": "This is a competitive rate! Would you like to proceed with this policy?"
        }
    
    # Fallback if comparison fails
    base_rates = {"life": 0.25, "property": 0.40, "vehicle": 1.5}
    rate = base_rates.get(policy_type, 0.30)
    monthly = coverage_amount * rate / 1000
    
    return {
        "policy_type": policy_type.title(),
        "coverage_amount": f"£{coverage_amount:,}",
        "monthly_premium": f"£{monthly:.2f}",
        "annual_premium": f"£{monthly * 12:,.2f}",
        "message": "Would you like to proceed with this policy?"
    }


import json

def purchase_policy_tool(customer_id: str, policy_type: str, coverage_amount: float,
                          monthly_premium: float, term_years: int = 1,
                          policy_details_json: str = "{}") -> dict:
    """
    Complete a policy purchase for a customer.
    
    Args:
        customer_id: The customer's ID
        policy_type: Type of policy (life, property, vehicle)
        coverage_amount: Coverage amount in dollars
        monthly_premium: Monthly premium amount
        term_years: Policy term in years (default: 1)
        policy_details_json: Optional type-specific details as a JSON string
        
    Returns:
        Purchase confirmation with policy details
    """
    # Parse policy details from JSON string
    try:
        details = json.loads(policy_details_json)
    except Exception as e:
        print(f"Error parsing policy details JSON: {e}")
        details = {}

    policy, message = create_policy(
        customer_id=customer_id,
        policy_type=policy_type,
        coverage_amount=coverage_amount,
        monthly_premium=monthly_premium,
        term_years=term_years,
        details=details
    )
    
    return {
        "success": True,
        "policy_id": policy["id"],
        "message": message
    }


def collect_life_policy_details_tool(beneficiary_name: str, beneficiary_relation: str,
                                      term_years: int, is_smoker: bool) -> dict:
    """
    Collect details needed for a life insurance policy.
    
    Args:
        beneficiary_name: Name of the beneficiary
        beneficiary_relation: Relationship (spouse, child, parent, other)
        term_years: Policy term in years (10, 15, 20, 30)
        is_smoker: Whether the applicant smokes
        
    Returns:
        Formatted life policy details for purchase
    """
    health_category = "standard" if is_smoker else "preferred"
    
    return {
        "details": {
            "beneficiary_name": beneficiary_name,
            "beneficiary_relation": beneficiary_relation,
            "term_years": term_years,
            "smoker": is_smoker,
            "health_category": health_category
        },
        "note": f"Term: {term_years} years, Health category: {health_category}"
    }


def collect_property_policy_details_tool(property_address: str, property_type: str,
                                          property_value: float, deductible: float,
                                          flood_coverage: bool = False) -> dict:
    """
    Collect details needed for a property insurance policy.
    
    Args:
        property_address: Full address of the property
        property_type: Type (house, apartment, condo)
        property_value: Estimated property value
        deductible: Deductible amount
        flood_coverage: Whether to include flood coverage
        
    Returns:
        Formatted property policy details for purchase
    """
    return {
        "details": {
            "property_address": property_address,
            "property_type": property_type,
            "property_value": property_value,
            "deductible": deductible,
            "flood_coverage": flood_coverage,
            "fire_coverage": True  # Always included
        },
        "note": f"Property type: {property_type}, Deductible: ${deductible:,}"
    }


def collect_vehicle_policy_details_tool(vehicle_vin: str, make: str, model: str,
                                         year: int, coverage_type: str,
                                         deductible: float = 500) -> dict:
    """
    Collect details needed for a vehicle insurance policy.
    
    Args:
        vehicle_vin: Vehicle Identification Number
        make: Vehicle make (e.g., Honda, Toyota)
        model: Vehicle model (e.g., Accord, Camry)
        year: Vehicle year
        coverage_type: Type (liability, collision, comprehensive)
        deductible: Deductible amount (default: $500)
        
    Returns:
        Formatted vehicle policy details for purchase
    """
    return {
        "details": {
            "vehicle_vin": vehicle_vin,
            "make": make,
            "model": model,
            "year": year,
            "coverage_type": coverage_type,
            "deductible": deductible
        },
        "note": f"{year} {make} {model}, Coverage: {coverage_type.title()}"
    }


# Create the agent
purchase_agent = Agent(
    model='gemini-2.5-flash',
    name='purchase_agent',
    description='Handles new policy purchases - provides quotes, collects details, and completes purchases.',
    instruction="""You are the Purchase Agent for Aviva Insurance.

You guide customers through the policy purchase process.

Purchase flow:
1. Understand what type of coverage they need (life, property, vehicle)
2. Determine the coverage amount they want
3. Provide a quote using get_quote_tool
4. Collect type-specific details:
   - Life: beneficiary, term, smoking status
   - Property: address, property type, deductible preferences
   - Vehicle: VIN, make/model/year, coverage type
5. Complete the purchase with purchase_policy_tool

Guidelines:
- Be enthusiastic but not pushy
- Explain coverage options clearly
- Help customers choose appropriate coverage amounts
- Highlight competitive rates and savings
- Confirm all details before finalizing purchase
- Celebrate with them when purchase is complete!
- Use British English spelling (e.g., 'cheque', 'centre') and tone.

Always ensure the customer understands what they're buying and feels confident in their decision.""",
    tools=[
        FunctionTool(func=get_quote_tool),
        FunctionTool(func=purchase_policy_tool),
        FunctionTool(func=collect_life_policy_details_tool),
        FunctionTool(func=collect_property_policy_details_tool),
        FunctionTool(func=collect_vehicle_policy_details_tool)
    ]
)
