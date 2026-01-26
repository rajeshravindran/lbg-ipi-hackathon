"""
Data Tools Module
=================
Provides functions for loading, saving, and querying JSON data stores.
All data operations are centralized here for maintainability.
"""

import json
from pathlib import Path
from typing import Optional, Any
from datetime import datetime

# Get the data directory path relative to this file
DATA_DIR = Path(__file__).parent.parent / "data"


def load_json(filename: str) -> list[dict]:
    """
    Load JSON data from a file in the data directory.
    
    Args:
        filename: Name of the JSON file (e.g., 'customers.json')
        
    Returns:
        List of dictionaries containing the data
        
    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    filepath = DATA_DIR / filename
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(filename: str, data: list[dict]) -> None:
    """
    Save data to a JSON file in the data directory.
    
    Args:
        filename: Name of the JSON file
        data: List of dictionaries to save
    """
    filepath = DATA_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)


def get_customer_by_id(customer_id: str) -> Optional[dict]:
    """
    Retrieve a customer by their unique ID.
    
    Args:
        customer_id: The customer's unique identifier (e.g., 'CUST001')
        
    Returns:
        Customer dictionary if found, None otherwise
    """
    customers = load_json("customers.json")
    for customer in customers:
        if customer["id"] == customer_id:
            return customer
    return None


def get_customer_by_email(email: str) -> Optional[dict]:
    """
    Retrieve a customer by their email address.
    
    Args:
        email: The customer's email address
        
    Returns:
        Customer dictionary if found, None otherwise
    """
    customers = load_json("customers.json")
    for customer in customers:
        if customer["email"].lower() == email.lower():
            return customer
    return None


def get_customer_by_phone(phone: str) -> Optional[dict]:
    """
    Retrieve a customer by their phone number.
    
    Args:
        phone: The customer's phone number
        
    Returns:
        Customer dictionary if found, None otherwise
    """
    customers = load_json("customers.json")
    for customer in customers:
        if customer["phone"] == phone:
            return customer
    return None


def get_policies_by_customer(customer_id: str) -> list[dict]:
    """
    Get all policies belonging to a specific customer.
    
    Args:
        customer_id: The customer's unique identifier
        
    Returns:
        List of policy dictionaries
    """
    policies = load_json("policies.json")
    return [p for p in policies if p["customer_id"] == customer_id]


def get_policy_by_id(policy_id: str) -> Optional[dict]:
    """
    Retrieve a policy by its unique ID.
    
    Args:
        policy_id: The policy's unique identifier (e.g., 'POL001')
        
    Returns:
        Policy dictionary if found, None otherwise
    """
    policies = load_json("policies.json")
    for policy in policies:
        if policy["id"] == policy_id:
            return policy
    return None


def get_policy_details(policy_id: str, policy_type: str) -> Optional[dict]:
    """
    Get type-specific details for a policy.
    
    Args:
        policy_id: The policy's unique identifier
        policy_type: Type of policy ('life', 'property', 'vehicle')
        
    Returns:
        Policy details dictionary if found, None otherwise
    """
    type_to_file = {
        "life": "life_policies.json",
        "property": "property_policies.json",
        "vehicle": "vehicle_policies.json"
    }
    
    if policy_type not in type_to_file:
        return None
        
    details = load_json(type_to_file[policy_type])
    for detail in details:
        if detail["policy_id"] == policy_id:
            return detail
    return None


def get_life_events_by_customer(customer_id: str, processed: Optional[bool] = None) -> list[dict]:
    """
    Get life events for a customer, optionally filtered by processed status.
    
    Args:
        customer_id: The customer's unique identifier
        processed: If specified, filter by this processed status
        
    Returns:
        List of life event dictionaries
    """
    events = load_json("life_events.json")
    filtered = [e for e in events if e["customer_id"] == customer_id]
    
    if processed is not None:
        filtered = [e for e in filtered if e["processed"] == processed]
    
    return filtered


def get_offers(offer_type: Optional[str] = None, active_only: bool = True) -> list[dict]:
    """
    Get promotional offers, optionally filtered by type.
    
    Args:
        offer_type: Filter by offer type ('discount', 'retention', 'loyalty', 'bonus_coverage')
        active_only: If True, only return active offers
        
    Returns:
        List of offer dictionaries
    """
    offers = load_json("offers.json")
    
    if active_only:
        offers = [o for o in offers if o["active"]]
    
    if offer_type:
        offers = [o for o in offers if o["offer_type"] == offer_type]
    
    return offers


def get_competitors() -> list[dict]:
    """
    Get competitor policy data for comparison.
    
    Returns:
        List of competitor dictionaries with their policies
    """
    return load_json("competitors.json")


def add_customer(customer_data: dict) -> dict:
    """
    Add a new customer to the database.
    
    Args:
        customer_data: Dictionary containing customer information
        
    Returns:
        The created customer record with assigned ID
    """
    customers = load_json("customers.json")
    
    # Generate new ID
    max_id = max([int(c["id"].replace("CUST", "")) for c in customers], default=0)
    new_id = f"CUST{max_id + 1:03d}"
    
    # Create customer record
    new_customer = {
        "id": new_id,
        "name": customer_data.get("name"),
        "email": customer_data.get("email"),
        "phone": customer_data.get("phone"),
        "dob": customer_data.get("dob"),
        "ssn_last4": customer_data.get("ssn_last4", ""),
        "customer_type": "existing",  # Once registered, they're existing
        "registration_date": datetime.now().isoformat(),
        "address": customer_data.get("address", "")
    }
    
    customers.append(new_customer)
    save_json("customers.json", customers)
    
    return new_customer


def add_transaction(policy_id: str, transaction_type: str, amount: float, description: str) -> dict:
    """
    Record a new transaction.
    
    Args:
        policy_id: ID of the policy
        transaction_type: Type of transaction
        amount: Transaction amount
        description: Transaction description
        
    Returns:
        The created transaction record
    """
    transactions = load_json("transactions.json")
    
    # Generate new ID
    max_id = max([int(t["id"].replace("TXN", "")) for t in transactions], default=0)
    new_id = f"TXN{max_id + 1:03d}"
    
    new_transaction = {
        "id": new_id,
        "policy_id": policy_id,
        "type": transaction_type,
        "amount": amount,
        "transaction_date": datetime.now().isoformat(),
        "description": description
    }
    
    transactions.append(new_transaction)
    save_json("transactions.json", transactions)
    
    return new_transaction
