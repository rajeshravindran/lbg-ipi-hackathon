"""
Authentication Agent
=====================
Handles customer identification and verification.
Determines if customer is new or existing and manages the appropriate flow.
"""

from google.adk.agents.llm_agent import Agent
from google.adk.tools import FunctionTool

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.auth_tools import (
    lookup_customer,
    verify_existing_customer,
    register_new_customer,
    get_customer_summary
)


# Wrap functions as ADK tools
def lookup_customer_tool(identifier: str) -> dict:
    """
    Look up a customer by their email, phone number, or policy number.
    Use this to determine if someone is a new or existing customer.
    
    Args:
        identifier: The customer's email, phone, or policy number
        
    Returns:
        Customer information if found, or indication they are new
    """
    customer, id_type = lookup_customer(identifier)
    if customer:
        return {
            "found": True,
            "customer_id": customer["id"],
            "customer_name": customer["name"],
            "customer_type": "existing",
            "identifier_type": id_type,
            "message": f"Found existing customer: {customer['name']}. Please verify their identity."
        }
    return {
        "found": False,
        "customer_type": "new",
        "message": "No customer found with this information. This appears to be a new customer."
    }


def verify_customer_tool(customer_id: str, date_of_birth: str, ssn_last_four: str) -> dict:
    """
    Verify an existing customer's identity using their date of birth and last 4 SSN digits.
    
    Args:
        customer_id: The customer's ID from the lookup
        date_of_birth: Date of birth in YYYY-MM-DD format
        ssn_last_four: Last 4 digits of Social Security Number
        
    Returns:
        Verification result with success status and message
    """
    success, message = verify_existing_customer(customer_id, date_of_birth, ssn_last_four)
    return {
        "verified": success,
        "message": message,
        "customer_id": customer_id if success else None
    }


def register_customer_tool(name: str, email: str, phone: str, 
                           date_of_birth: str, address: str = "") -> dict:
    """
    Register a new customer in the system.
    
    Args:
        name: Customer's full name
        email: Customer's email address
        phone: Customer's phone number (format: XXX-XXXX)
        date_of_birth: Date of birth in YYYY-MM-DD format
        address: Optional physical address
        
    Returns:
        New customer record and welcome message
    """
    customer, message = register_new_customer(name, email, phone, date_of_birth, address)
    return {
        "success": "already exists" not in message.lower(),
        "customer_id": customer["id"],
        "message": message
    }


def get_customer_profile_tool(customer_id: str) -> dict:
    """
    Get a summary of a verified customer's profile and policies.
    
    Args:
        customer_id: The verified customer's ID
        
    Returns:
        Formatted customer summary
    """
    summary = get_customer_summary(customer_id)
    return {"summary": summary}


# Create the agent
auth_agent = Agent(
    model='gemini-2.5-flash',
    name='auth_agent',
    description='Handles customer identification and authentication. Determines if a customer is new or existing and manages verification.',
    instruction="""You are the Authentication Agent for Aviva Insurance.
    
Your responsibilities:
1. Identify customers: Ask for their email, phone, or policy number to look them up
2. For EXISTING customers: Verify their identity by asking for date of birth and last 4 SSN digits
3. For NEW customers: Collect their information (name, email, phone, DOB) to register them

Always be polite, professional, and security-conscious. Never skip verification steps for existing customers.

Flow:
1. Greet the customer and ask for an identifier (email, phone, or policy number)
2. Use lookup_customer_tool to check if they exist
3. If existing: Ask for DOB and last 4 SSN, then verify with verify_customer_tool
4. If new: Welcome them and collect their information, then use register_customer_tool
5. Once verified/registered, provide their profile summary

Tone:
- Use British English spelling.
- Be polite and respectful ("Could you please...", "Thank you kindly").

Be formal and professional at all times. Protect customer information.""",
    tools=[
        FunctionTool(func=lookup_customer_tool),
        FunctionTool(func=verify_customer_tool),
        FunctionTool(func=register_customer_tool),
        FunctionTool(func=get_customer_profile_tool)
    ]
)
