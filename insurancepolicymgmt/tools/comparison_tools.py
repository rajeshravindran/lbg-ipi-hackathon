"""
Comparison Tools Module
========================
Compares policies with competitor offerings.
Supports real API integration with fallback to synthetic data.
"""

import os
from typing import Optional
from tools.data_tools import get_competitors, get_policy_by_id


def compare_policies(policy_type: str, coverage_amount: float, 
                     our_premium: Optional[float] = None) -> str:
    """
    Compare policy options across competitors.
    Uses real API if configured, otherwise falls back to synthetic data.
    
    Args:
        policy_type: Type of policy ('life', 'property', 'vehicle')
        coverage_amount: Desired coverage amount
        our_premium: Our current premium (if comparing existing policy)
        
    Returns:
        Formatted comparison table as string
    """
    # Check if real API is enabled
    api_enabled = os.getenv("COMPARISON_API_ENABLED", "false").lower() == "true"
    
    if api_enabled:
        # Try to fetch from real API
        api_data = _fetch_from_api(policy_type, coverage_amount)
        if api_data:
            return _format_comparison(api_data, policy_type, coverage_amount, our_premium)
    
    # Fall back to synthetic data
    return _compare_with_synthetic(policy_type, coverage_amount, our_premium)


def _fetch_from_api(policy_type: str, coverage_amount: float) -> Optional[list]:
    """
    Fetch competitor rates from external API.
    This is a placeholder for real API integration.
    
    Returns:
        List of competitor quotes or None if API unavailable
    """
    # TODO: Implement real API integration
    # Example providers: Bindable API, If Insurance API
    # 
    # api_key = os.getenv("COMPARISON_API_KEY")
    # if not api_key:
    #     return None
    #
    # response = requests.get(
    #     "https://api.example.com/quotes",
    #     params={"type": policy_type, "coverage": coverage_amount},
    #     headers={"Authorization": f"Bearer {api_key}"}
    # )
    # return response.json()
    
    return None  # API not implemented yet


def _compare_with_synthetic(policy_type: str, coverage_amount: float,
                            our_premium: Optional[float] = None) -> str:
    """
    Compare using synthetic competitor data.
    
    Args:
        policy_type: Type of policy
        coverage_amount: Desired coverage amount
        our_premium: Our current premium for comparison
        
    Returns:
        Formatted comparison string
    """
    competitors = get_competitors()
    comparison_data = []
    
    for competitor in competitors:
        for policy in competitor["policies"]:
            if policy["policy_type"] == policy_type:
                # Scale premium based on coverage difference
                base_coverage = policy["coverage_amount"]
                base_premium = policy["monthly_premium"]
                
                # Simple linear scaling for demo purposes
                scaled_premium = round(base_premium * (coverage_amount / base_coverage), 2)
                
                comparison_data.append({
                    "provider": competitor["provider"],
                    "premium": scaled_premium,
                    "features": policy.get("features", [])
                })
    
    return _format_comparison(comparison_data, policy_type, coverage_amount, our_premium)


def _format_comparison(data: list, policy_type: str, coverage_amount: float,
                       our_premium: Optional[float] = None) -> str:
    """
    Format comparison data into a readable table.
    
    Args:
        data: List of competitor quotes
        policy_type: Type of policy
        coverage_amount: Coverage amount
        our_premium: Our premium for comparison
        
    Returns:
        Formatted comparison string
    """
    # Sort by premium (lowest first)
    data.sort(key=lambda x: x["premium"])
    
    result = f"## {policy_type.title()} Insurance Comparison\n"
    result += f"**Coverage Amount:** £{coverage_amount:,.0f}\n\n"
    
    # Build comparison table
    result += "| Provider | Monthly Premium | Annual Cost | Key Features |\n"
    result += "|----------|-----------------|-------------|-------------|\n"
    
    # Add our offering first if premium provided
    if our_premium:
        annual = our_premium * 12
        result += f"| **Aviva (You)** | **£{our_premium:.2f}** | **£{annual:,.2f}** | Your current policy |\n"
    
    for item in data:
        annual = item["premium"] * 12
        features = ", ".join(item["features"][:2]) if item["features"] else "Standard coverage"
        result += f"| {item['provider']} | £{item['premium']:.2f} | £{annual:,.2f} | {features} |\n"
    
    # Add summary
    if data:
        lowest = data[0]
        highest = data[-1]
        
        result += f"\n**Market Summary:**\n"
        result += f"- Lowest premium: {lowest['provider']} at £{lowest['premium']:.2f}/month\n"
        result += f"- Highest premium: {highest['provider']} at £{highest['premium']:.2f}/month\n"
        
        if our_premium:
            avg_premium = sum(d["premium"] for d in data) / len(data)
            if our_premium < avg_premium:
                savings = ((avg_premium - our_premium) / avg_premium) * 100
                result += f"- Your rate is **{savings:.1f}% below** the market average!\n"
            else:
                result += f"- Market average: £{avg_premium:.2f}/month\n"
    
    return result


def compare_customer_policy(policy_id: str) -> str:
    """
    Compare a customer's existing policy with competitors.
    
    Args:
        policy_id: ID of the customer's policy
        
    Returns:
        Formatted comparison string
    """
    policy = get_policy_by_id(policy_id)
    
    if not policy:
        return f"Policy {policy_id} not found."
    
    return compare_policies(
        policy["policy_type"],
        policy["coverage_amount"],
        policy["monthly_premium"]
    )


def get_best_quote(policy_type: str, coverage_amount: float) -> dict:
    """
    Get the best available quote for a policy type.
    
    Args:
        policy_type: Type of policy
        coverage_amount: Desired coverage amount
        
    Returns:
        Dictionary with provider and premium info
    """
    competitors = get_competitors()
    best_quote = None
    
    for competitor in competitors:
        for policy in competitor["policies"]:
            if policy["policy_type"] == policy_type:
                base_coverage = policy["coverage_amount"]
                base_premium = policy["monthly_premium"]
                scaled_premium = round(base_premium * (coverage_amount / base_coverage), 2)
                
                if best_quote is None or scaled_premium < best_quote["premium"]:
                    best_quote = {
                        "provider": competitor["provider"],
                        "premium": scaled_premium,
                        "features": policy.get("features", [])
                    }
    
    # Add our competitive rate (10% better than best competitor)
    if best_quote:
        our_premium = round(best_quote["premium"] * 0.90, 2)
        return {
            "our_premium": our_premium,
            "best_competitor": best_quote["provider"],
            "competitor_premium": best_quote["premium"],
            "savings": round(best_quote["premium"] - our_premium, 2)
        }
    
    return {}
