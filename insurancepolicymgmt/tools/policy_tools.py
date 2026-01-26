"""
Policy Tools Module
====================
Provides CRUD operations for insurance policies.
Handles creation, updates, renewals, cancellations, and coverage modifications.
"""

from typing import Optional, Tuple
from datetime import datetime, timedelta
from tools.data_tools import (
    load_json, save_json,
    get_policy_by_id, get_policies_by_customer,
    add_transaction
)


def create_policy(customer_id: str, policy_type: str, coverage_amount: float,
                  monthly_premium: float, term_years: int = 1,
                  details: Optional[dict] = None) -> Tuple[dict, str]:
    """
    Create a new insurance policy for a customer.
    
    Args:
        customer_id: ID of the customer
        policy_type: Type of policy ('life', 'property', 'vehicle')
        coverage_amount: Coverage amount in dollars
        monthly_premium: Monthly premium amount
        term_years: Policy term in years (default 1)
        details: Type-specific policy details
        
    Returns:
        Tuple of (policy_record, confirmation_message)
    """
    policies = load_json("policies.json")
    
    # Generate new policy ID
    max_id = max([int(p["id"].replace("POL", "")) for p in policies], default=0)
    new_id = f"POL{max_id + 1:03d}"
    
    now = datetime.now()
    end_date = now + timedelta(days=365 * term_years)
    
    new_policy = {
        "id": new_id,
        "customer_id": customer_id,
        "policy_type": policy_type,
        "status": "active",
        "coverage_amount": coverage_amount,
        "monthly_premium": monthly_premium,
        "start_date": now.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    policies.append(new_policy)
    save_json("policies.json", policies)
    
    # Add type-specific details if provided
    if details:
        _add_policy_details(new_id, policy_type, details)
    
    # Record transaction
    annual_premium = monthly_premium * 12
    add_transaction(new_id, "purchase", annual_premium, 
                    f"Initial {policy_type} policy purchase - annual premium")
    
    message = (
        f"Congratulations! Your {policy_type.title()} Insurance policy has been created.\n"
        f"Policy ID: {new_id}\n"
        f"Coverage: £{coverage_amount:,.0f}\n"
        f"Monthly Premium: £{monthly_premium:.2f}\n"
        f"Effective: {new_policy['start_date']} to {new_policy['end_date']}"
    )
    
    return new_policy, message


def _add_policy_details(policy_id: str, policy_type: str, details: dict) -> None:
    """Add type-specific policy details to the appropriate JSON file."""
    type_to_file = {
        "life": "life_policies.json",
        "property": "property_policies.json",
        "vehicle": "vehicle_policies.json"
    }
    
    if policy_type not in type_to_file:
        return
    
    filename = type_to_file[policy_type]
    existing = load_json(filename)
    
    # Generate new detail ID
    prefix = {"life": "LP", "property": "PP", "vehicle": "VP"}[policy_type]
    max_id = max([int(d["id"].replace(prefix, "")) for d in existing], default=0)
    new_id = f"{prefix}{max_id + 1:03d}"
    
    details["id"] = new_id
    details["policy_id"] = policy_id
    
    existing.append(details)
    save_json(filename, existing)


def update_policy(policy_id: str, updates: dict) -> Tuple[bool, str]:
    """
    Update an existing policy's attributes.
    
    Args:
        policy_id: ID of the policy to update
        updates: Dictionary of fields to update
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    policies = load_json("policies.json")
    
    for i, policy in enumerate(policies):
        if policy["id"] == policy_id:
            # Prevent updating certain fields
            protected_fields = {"id", "customer_id", "created_at"}
            for field in protected_fields:
                updates.pop(field, None)
            
            # Apply updates
            policies[i].update(updates)
            policies[i]["updated_at"] = datetime.now().isoformat()
            
            save_json("policies.json", policies)
            return True, f"Policy {policy_id} has been updated successfully."
    
    return False, f"Policy {policy_id} not found."


def renew_policy(policy_id: str, term_years: int = 1) -> Tuple[bool, str]:
    """
    Renew an existing policy for another term.
    
    Args:
        policy_id: ID of the policy to renew
        term_years: Renewal term in years
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    policy = get_policy_by_id(policy_id)
    
    if not policy:
        return False, f"Policy {policy_id} not found."
    
    if policy["status"] == "cancelled":
        return False, "Cannot renew a cancelled policy. Please create a new policy."
    
    # Calculate new end date
    current_end = datetime.strptime(policy["end_date"], "%Y-%m-%d")
    new_end = current_end + timedelta(days=365 * term_years)
    
    updates = {
        "end_date": new_end.strftime("%Y-%m-%d"),
        "status": "active"
    }
    
    success, _ = update_policy(policy_id, updates)
    
    if success:
        # Record transaction
        annual_premium = policy["monthly_premium"] * 12
        add_transaction(policy_id, "renewal", annual_premium, 
                        f"Policy renewal for {term_years} year(s)")
        
        return True, (
            f"Your {policy['policy_type'].title()} Insurance policy has been renewed!\n"
            f"New expiration date: {new_end.strftime('%Y-%m-%d')}\n"
            f"Annual premium charged: £{annual_premium:,.2f}"
        )
    
    return False, "Failed to renew policy. Please contact support."


def cancel_policy(policy_id: str, reason: str = "") -> Tuple[bool, str, float]:
    """
    Cancel an insurance policy.
    
    Args:
        policy_id: ID of the policy to cancel
        reason: Optional cancellation reason
        
    Returns:
        Tuple of (success: bool, message: str, refund_amount: float)
    """
    policy = get_policy_by_id(policy_id)
    
    if not policy:
        return False, f"Policy {policy_id} not found.", 0.0
    
    if policy["status"] == "cancelled":
        return False, "This policy is already cancelled.", 0.0
    
    # Calculate prorated refund
    end_date = datetime.strptime(policy["end_date"], "%Y-%m-%d")
    days_remaining = (end_date - datetime.now()).days
    
    if days_remaining > 0:
        annual_premium = policy["monthly_premium"] * 12
        daily_rate = annual_premium / 365
        refund = round(daily_rate * days_remaining, 2)
    else:
        refund = 0.0
    
    updates = {"status": "cancelled"}
    success, _ = update_policy(policy_id, updates)
    
    if success:
        description = f"Policy cancellation"
        if reason:
            description += f" - Reason: {reason}"
        if refund > 0:
            description += f" - Refund for {days_remaining} remaining days"
        
        add_transaction(policy_id, "cancellation", -refund, description)
        
        message = f"Your {policy['policy_type'].title()} Insurance policy has been cancelled."
        if refund > 0:
            message += f"\nA refund of £{refund:,.2f} will be processed within 5-7 business days."
        
        return True, message, refund
    
    return False, "Failed to cancel policy. Please contact support.", 0.0


def modify_coverage(policy_id: str, new_coverage: float) -> Tuple[bool, str]:
    """
    Modify the coverage amount of an existing policy.
    
    Args:
        policy_id: ID of the policy to modify
        new_coverage: New coverage amount in dollars
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    policy = get_policy_by_id(policy_id)
    
    if not policy:
        return False, f"Policy {policy_id} not found."
    
    if policy["status"] != "active":
        return False, "Can only modify coverage on active policies."
    
    old_coverage = policy["coverage_amount"]
    
    # Calculate new premium (simplified: proportional to coverage)
    ratio = new_coverage / old_coverage
    new_premium = round(policy["monthly_premium"] * ratio, 2)
    
    updates = {
        "coverage_amount": new_coverage,
        "monthly_premium": new_premium
    }
    
    success, _ = update_policy(policy_id, updates)
    
    if success:
        change_type = "increased" if new_coverage > old_coverage else "decreased"
        
        # Record transaction for the premium difference
        premium_diff = (new_premium - policy["monthly_premium"]) * 12
        if abs(premium_diff) > 0:
            add_transaction(policy_id, "modification", premium_diff,
                           f"Coverage {change_type} from £{old_coverage:,.0f} to £{new_coverage:,.0f}")
        
        return True, (
            f"Your coverage has been {change_type}!\n"
            f"New Coverage: £{new_coverage:,.0f}\n"
            f"New Monthly Premium: £{new_premium:.2f}"
        )
    
    return False, "Failed to modify coverage. Please contact support."


def list_customer_policies(customer_id: str, include_cancelled: bool = False) -> str:
    """
    Get a formatted list of all policies for a customer.
    
    Args:
        customer_id: ID of the customer
        include_cancelled: Whether to include cancelled policies
        
    Returns:
        Formatted string listing all policies
    """
    policies = get_policies_by_customer(customer_id)
    
    if not include_cancelled:
        policies = [p for p in policies if p["status"] != "cancelled"]
    
    if not policies:
        return "You don't have any active policies."
    
    result = "**Your Insurance Policies:**\n\n"
    
    for policy in policies:
        status_emoji = "✅" if policy["status"] == "active" else "❌"
        result += f"{status_emoji} **{policy['policy_type'].title()} Insurance** (ID: {policy['id']})\n"
        result += f"   Coverage: £{policy['coverage_amount']:,.0f}\n"
        result += f"   Monthly Premium: £{policy['monthly_premium']:.2f}\n"
        result += f"   Status: {policy['status'].title()}\n"
        result += f"   Valid: {policy['start_date']} to {policy['end_date']}\n\n"
    
    return result.strip()
