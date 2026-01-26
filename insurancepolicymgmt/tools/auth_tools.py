"""
Authentication Tools Module
============================
Handles customer identification, verification, and registration.
Implements differentiated authentication flows for new vs existing customers.
"""

from typing import Optional, Tuple
from tools.data_tools import (
    get_customer_by_email,
    get_customer_by_phone,
    get_policy_by_id,
    get_customer_by_id,
    add_customer
)


def lookup_customer(identifier: str) -> Tuple[Optional[dict], str]:
    """
    Look up a customer by email, phone, or policy number.
    This determines if the user is a new or existing customer.
    
    Args:
        identifier: Email address, phone number, or policy ID
        
    Returns:
        Tuple of (customer_dict or None, identifier_type)
        identifier_type is one of: 'email', 'phone', 'policy', 'not_found'
    """
    # Try email lookup first
    if "@" in identifier:
        customer = get_customer_by_email(identifier)
        if customer:
            return customer, "email"
    
    # Try phone lookup (check for phone-like pattern)
    if any(c.isdigit() for c in identifier) and "-" in identifier:
        customer = get_customer_by_phone(identifier)
        if customer:
            return customer, "phone"
    
    # Try policy lookup
    if identifier.upper().startswith("POL"):
        policy = get_policy_by_id(identifier.upper())
        if policy:
            customer = get_customer_by_id(policy["customer_id"])
            if customer:
                return customer, "policy"
    
    return None, "not_found"


def verify_existing_customer(customer_id: str, dob: str, ssn_last4: str) -> Tuple[bool, str]:
    """
    Verify an existing customer's identity using DOB and last 4 SSN.
    This is a lightweight verification for returning customers.
    
    Args:
        customer_id: The customer's ID from lookup
        dob: Date of birth in YYYY-MM-DD format
        ssn_last4: Last 4 digits of SSN
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    customer = get_customer_by_id(customer_id)
    
    if not customer:
        return False, "Customer not found. Please check your information."
    
    # Verify DOB
    if customer.get("dob") != dob:
        return False, "The date of birth provided does not match our records."
    
    # Verify SSN last 4
    if customer.get("ssn_last4") != ssn_last4:
        return False, "The SSN digits provided do not match our records."
    
    return True, f"Welcome back, {customer['name']}! Your identity has been verified."


def register_new_customer(name: str, email: str, phone: str, dob: str, 
                          address: str = "", ssn_last4: str = "") -> Tuple[dict, str]:
    """
    Register a new customer in the system.
    
    Args:
        name: Customer's full name
        email: Customer's email address
        phone: Customer's phone number
        dob: Date of birth in YYYY-MM-DD format
        address: Optional physical address
        ssn_last4: Optional last 4 digits of SSN
        
    Returns:
        Tuple of (customer_record, welcome_message)
    """
    # Check if email already exists
    existing = get_customer_by_email(email)
    if existing:
        return existing, f"An account with email {email} already exists. Please log in instead."
    
    # Check if phone already exists
    existing = get_customer_by_phone(phone)
    if existing:
        return existing, f"An account with phone {phone} already exists. Please log in instead."
    
    # Create new customer
    customer_data = {
        "name": name,
        "email": email,
        "phone": phone,
        "dob": dob,
        "address": address,
        "ssn_last4": ssn_last4
    }
    
    new_customer = add_customer(customer_data)
    
    welcome_message = (
        f"Welcome to Aviva Insurance, {name}! "
        f"Your account has been created successfully. "
        f"Your customer ID is {new_customer['id']}. "
        f"You can now explore our insurance options."
    )
    
    return new_customer, welcome_message


def get_customer_summary(customer_id: str) -> str:
    """
    Get a summary of customer information for display.
    Used after successful authentication.
    
    Args:
        customer_id: The customer's ID
        
    Returns:
        Formatted string with customer summary
    """
    from tools.data_tools import get_policies_by_customer
    
    customer = get_customer_by_id(customer_id)
    if not customer:
        return "Customer not found."
    
    policies = get_policies_by_customer(customer_id)
    active_policies = [p for p in policies if p["status"] == "active"]
    
    summary = f"""
**Customer Profile**
- Name: {customer['name']}
- Email: {customer['email']}
- Phone: {customer['phone']}
- Member Since: {customer['registration_date'][:10]}

**Policy Summary**
- Total Policies: {len(policies)}
- Active Policies: {len(active_policies)}
"""
    
    if active_policies:
        summary += "\n**Active Coverage:**\n"
        for policy in active_policies:
            summary += f"- {policy['policy_type'].title()}: ${policy['coverage_amount']:,.0f} coverage\n"
    
    return summary.strip()
