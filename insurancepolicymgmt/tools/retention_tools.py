"""
Retention Tools Module
=======================
Handles customer retention when they attempt to cancel policies.
Provides offers, discounts, and incentives to retain customers.
"""

from typing import Tuple, Optional
from tools.data_tools import (
    get_offers, get_customer_by_id, get_policies_by_customer,
    load_json, save_json
)
from tools.policy_tools import update_policy


def get_retention_offers(customer_id: str, policy_id: str) -> list[dict]:
    """
    Get available retention offers for a customer attempting to cancel.
    Offers are personalized based on customer tenure and policy value.
    
    Args:
        customer_id: ID of the customer
        policy_id: ID of the policy they want to cancel
        
    Returns:
        List of applicable retention offers
    """
    customer = get_customer_by_id(customer_id)
    if not customer:
        return []
    
    # Get all retention-type offers
    retention_offers = get_offers(offer_type="retention")
    
    # Get customer's policies to check loyalty
    all_policies = get_policies_by_customer(customer_id)
    active_policies = [p for p in all_policies if p["status"] == "active"]
    
    # Calculate customer value
    total_monthly_premium = sum(p["monthly_premium"] for p in active_policies)
    
    # Personalize offers based on customer value
    personalized_offers = []
    
    for offer in retention_offers:
        offer_copy = offer.copy()
        
        # High-value customers get the best offers
        if total_monthly_premium > 300:
            # Give them all offers including the best ones
            personalized_offers.append(offer_copy)
        elif total_monthly_premium > 150:
            # Medium value - exclude the highest discount
            if offer["discount_percent"] <= 25:
                personalized_offers.append(offer_copy)
        else:
            # Standard customers get basic retention offers
            if offer["discount_percent"] <= 20:
                personalized_offers.append(offer_copy)
    
    return personalized_offers


def present_retention_offers(customer_id: str, policy_id: str) -> str:
    """
    Present retention offers to a customer in a formatted way.
    This should be called when a customer expresses intent to cancel.
    
    Args:
        customer_id: ID of the customer
        policy_id: ID of the policy they want to cancel
        
    Returns:
        Formatted string presenting available offers
    """
    offers = get_retention_offers(customer_id, policy_id)
    
    if not offers:
        return "I understand you'd like to cancel. Let me process that for you."
    
    result = """## Before You Go... 🤝

We truly value you as a customer and would hate to see you leave. 
Here are some exclusive offers we'd like to extend to you:

"""
    
    for i, offer in enumerate(offers, 1):
        result += f"### Option {i}: {offer['name']}\n"
        if offer["discount_percent"] > 0:
            result += f"💰 **{offer['discount_percent']}% Discount** on your premium\n"
        result += f"📋 {offer['description']}\n\n"
    
    result += """---
**Would you like to accept any of these offers instead of cancelling?**

Just let me know which option interests you, or if you'd still like to proceed with the cancellation.
"""
    
    return result


def apply_retention_offer(customer_id: str, policy_id: str, offer_id: str) -> Tuple[bool, str]:
    """
    Apply a retention offer to a customer's policy.
    
    Args:
        customer_id: ID of the customer
        policy_id: ID of the policy
        offer_id: ID of the offer to apply
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    # Verify offer exists and is valid
    offers = get_offers()
    offer = next((o for o in offers if o["id"] == offer_id), None)
    
    if not offer:
        return False, "Offer not found or has expired."
    
    # Get the policy
    from tools.data_tools import get_policy_by_id
    policy = get_policy_by_id(policy_id)
    
    if not policy:
        return False, "Policy not found."
    
    # Calculate new premium with discount
    if offer["discount_percent"] > 0:
        discount_multiplier = 1 - (offer["discount_percent"] / 100)
        new_premium = round(policy["monthly_premium"] * discount_multiplier, 2)
        old_premium = policy["monthly_premium"]
        
        # Update the policy
        success, _ = update_policy(policy_id, {"monthly_premium": new_premium})
        
        if success:
            savings = old_premium - new_premium
            annual_savings = savings * 12
            
            return True, f"""
## Offer Applied Successfully! 🎉

Thank you for choosing to stay with Aviva Insurance!

**{offer['name']}** has been applied to your policy.

- Previous Premium: £{old_premium:.2f}/month
- New Premium: £{new_premium:.2f}/month
- **You Save: £{savings:.2f}/month (£{annual_savings:.2f}/year)**

We're committed to providing you with the best coverage at the best value.
"""
    else:
        # Non-discount offers (like premium freeze)
        # These would require different handling in a real system
        return True, f"""
## Offer Applied Successfully! 🎉

Thank you for choosing to stay with Aviva Insurance!

**{offer['name']}** has been applied to your account.

{offer['description']}

We appreciate your loyalty and are committed to keeping you protected.
"""
    
    return False, "Failed to apply offer. Please contact support."


def get_cancellation_reasons() -> list[str]:
    """
    Get list of common cancellation reasons for survey.
    
    Returns:
        List of reason options
    """
    return [
        "Found cheaper coverage elsewhere",
        "No longer need this coverage",
        "Financial difficulties",
        "Poor customer service experience",
        "Coverage doesn't meet my needs",
        "Moving to a different provider",
        "Consolidating policies",
        "Other"
    ]


def process_cancellation_with_reason(policy_id: str, reason: str) -> str:
    """
    Process a cancellation and record the reason.
    This should only be called after retention offers have been declined.
    
    Args:
        policy_id: ID of the policy to cancel
        reason: Cancellation reason selected by customer
        
    Returns:
        Confirmation message
    """
    from tools.policy_tools import cancel_policy
    
    success, message, refund = cancel_policy(policy_id, reason)
    
    if success:
        result = f"""
## Cancellation Confirmed

{message}

We're sorry to see you go. Your feedback has been recorded:
- **Reason**: {reason}

If your circumstances change, we'd be happy to welcome you back.
Our door is always open, and we often have special offers for returning customers.

Thank you for being an Aviva customer. We wish you all the best.
"""
        return result
    
    return message


def calculate_loyalty_score(customer_id: str) -> dict:
    """
    Calculate a customer's loyalty score for internal use.
    Higher scores indicate more valuable customers who should
    receive better retention offers.
    
    Args:
        customer_id: ID of the customer
        
    Returns:
        Dictionary with loyalty metrics
    """
    from tools.data_tools import get_policies_by_customer
    from datetime import datetime
    
    customer = get_customer_by_id(customer_id)
    if not customer:
        return {"score": 0, "tier": "new"}
    
    policies = get_policies_by_customer(customer_id)
    active_policies = [p for p in policies if p["status"] == "active"]
    
    # Calculate tenure in years
    reg_date = datetime.fromisoformat(customer["registration_date"].replace("Z", "+00:00"))
    tenure_years = (datetime.now(reg_date.tzinfo) - reg_date).days / 365
    
    # Calculate total monthly premium
    total_premium = sum(p["monthly_premium"] for p in active_policies)
    
    # Score calculation
    score = 0
    score += min(tenure_years * 10, 50)  # Up to 50 points for tenure
    score += min(total_premium / 10, 30)  # Up to 30 points for premium
    score += len(active_policies) * 5     # 5 points per active policy
    
    # Determine tier
    if score >= 75:
        tier = "platinum"
    elif score >= 50:
        tier = "gold"
    elif score >= 25:
        tier = "silver"
    else:
        tier = "bronze"
    
    return {
        "score": round(score, 1),
        "tier": tier,
        "tenure_years": round(tenure_years, 1),
        "active_policies": len(active_policies),
        "monthly_premium": total_premium
    }
