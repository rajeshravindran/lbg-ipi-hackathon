"""
Customer Tools - Authentication, profile lookup, and customer creation.

These tools handle all customer-related operations including identity
verification for existing customers and registration for new customers.
"""

import json
import os
from datetime import datetime

# ------------------------------------------------------------------
# Data file path resolution
# ------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def _load_json(filename: str) -> list:
    """Load a JSON data file from the data directory."""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(filename: str, data: list) -> None:
    """Save data back to a JSON file in the data directory."""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ------------------------------------------------------------------
# Tool: Authenticate an existing customer
# ------------------------------------------------------------------
def authenticate_customer(
    policy_number: str,
    phone: str = "",
    email: str = "",
    dob: str = "",
    postcode: str = ""
) -> dict:
    """
    Authenticate an existing customer by verifying their identity.

    Requires the policy number and at least two of: phone, email,
    date of birth, or postcode to confirm the customer's identity.

    Args:
        policy_number: The customer's policy number (e.g. 'POL-AUTO-001').
        phone: Registered mobile number for verification.
        email: Registered email for verification.
        dob: Date of birth in YYYY-MM-DD format for verification.
        postcode: Registered postcode for verification.

    Returns:
        dict with status, customer_id and customer_name on success,
        or an error_message on failure.
    """
    # Load policies to find the customer_id linked to the policy
    policies = _load_json("policies.json")
    policy = next((p for p in policies if p["policy_id"] == policy_number), None)

    if not policy:
        return {
            "status": "error",
            "error_message": f"Policy '{policy_number}' not found. Please check the number and try again."
        }

    # Load customer data
    customers = _load_json("customers.json")
    customer = next((c for c in customers if c["customer_id"] == policy["customer_id"]), None)

    if not customer:
        return {
            "status": "error",
            "error_message": "Customer record not found for this policy."
        }

    # Verify identity — need at least 2 matching fields
    matches = 0
    if phone and phone == customer.get("auth_mobile", ""):
        matches += 1
    if email and email.lower() == customer.get("auth_email", "").lower():
        matches += 1
    if dob and dob == customer.get("date_of_birth", ""):
        matches += 1
    if postcode and postcode.upper().replace(" ", "") == customer["address"].get("postcode", "").upper().replace(" ", ""):
        matches += 1

    if matches >= 2:
        return {
            "status": "success",
            "customer_id": customer["customer_id"],
            "customer_name": f"{customer['first_name']} {customer['last_name']}",
            "message": f"Identity verified successfully. Welcome back, {customer['first_name']}!"
        }
    elif matches == 1:
        return {
            "status": "partial",
            "message": "Only one detail matched. Please provide additional verification details (phone, email, date of birth, or postcode)."
        }
    else:
        return {
            "status": "error",
            "error_message": "Verification failed. The details provided do not match our records. Please try again or contact support."
        }


# ------------------------------------------------------------------
# Tool: Get full customer profile
# ------------------------------------------------------------------
def get_customer_profile(customer_id: str) -> dict:
    """
    Retrieve the full profile of a customer.

    Args:
        customer_id: The unique customer identifier (e.g. 'CUST-001').

    Returns:
        dict with status and the full customer profile data,
        or an error_message if not found.
    """
    customers = _load_json("customers.json")
    customer = next((c for c in customers if c["customer_id"] == customer_id), None)

    if not customer:
        return {
            "status": "error",
            "error_message": f"Customer '{customer_id}' not found."
        }

    return {
        "status": "success",
        "customer": customer
    }


# ------------------------------------------------------------------
# Tool: Create a new customer record
# ------------------------------------------------------------------
def create_customer(
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    date_of_birth: str,
    street: str,
    city: str,
    postcode: str,
    driving_licence_number: str = "",
    licence_years: int = 0,
    ncd_years: int = 0
) -> dict:
    """
    Register a new customer in the system.

    Args:
        first_name: Customer's first name.
        last_name: Customer's last name.
        email: Customer's email address.
        phone: Customer's mobile phone number.
        date_of_birth: Date of birth in YYYY-MM-DD format.
        street: Street address.
        city: City.
        postcode: Postcode.
        driving_licence_number: UK driving licence number (optional).
        licence_years: Number of years holding a licence (optional).
        ncd_years: Number of no-claims discount years (optional).

    Returns:
        dict with status and the new customer_id on success.
    """
    customers = _load_json("customers.json")

    # Generate next customer ID
    existing_ids = [int(c["customer_id"].split("-")[1]) for c in customers]
    next_id = max(existing_ids) + 1 if existing_ids else 1
    new_id = f"CUST-{next_id:03d}"

    new_customer = {
        "customer_id": new_id,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "date_of_birth": date_of_birth,
        "address": {
            "street": street,
            "city": city,
            "postcode": postcode,
            "region": ""
        },
        "driving_licence_number": driving_licence_number,
        "licence_years": licence_years,
        "ncd_years": ncd_years,
        "customer_since": datetime.now().strftime("%Y-%m-%d"),
        "life_events": [],
        "auth_mobile": phone,
        "auth_email": email
    }

    customers.append(new_customer)
    _save_json("customers.json", customers)

    return {
        "status": "success",
        "customer_id": new_id,
        "message": f"Welcome, {first_name}! Your account has been created successfully."
    }
