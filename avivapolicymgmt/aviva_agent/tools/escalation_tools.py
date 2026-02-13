"""
Escalation Tools - Deterministic tool for routing customers to human agents.

Provides a reliable tool that always returns the correct Aviva contact
information, ensuring the LLM never "fails silently" on escalation.
"""


def escalate_to_human(policy_type: str = "general") -> dict:
    """
    Provide Aviva customer service contact details for human escalation.

    Call this tool whenever a customer asks to speak to a real person,
    wants to be transferred to a human agent, or agrees to be routed
    to a customer representative. The tool returns the correct phone
    number, opening hours, and a message to present to the customer.

    Args:
        policy_type: The type of policy the enquiry relates to.
                     One of 'car', 'motor', 'auto', 'home', 'property',
                     or 'general'. Defaults to 'general'.

    Returns:
        dict with status, phone number, opening hours, and a formatted
        message to present to the customer.
    """
    policy_type_lower = policy_type.lower().strip()

    if policy_type_lower in ("car", "motor", "auto"):
        phone = "0800 051 0960"
        department = "Car Insurance"
        hours = "Mon-Fri 8am-8pm, Sat 9am-5pm"
    elif policy_type_lower in ("home", "property"):
        phone = "0800 051 0961"
        department = "Home Insurance"
        hours = "Mon-Fri 8am-8pm, Sat 9am-5pm"
    else:
        phone = "0800 051 0962"
        department = "General Enquiries"
        hours = "Mon-Fri 8am-6pm"

    return {
        "status": "success",
        "department": department,
        "phone_number": phone,
        "opening_hours": hours,
        "message": (
            f"I'd be happy to connect you with our {department} team. "
            f"You can reach them on **{phone}** ({hours}). "
            f"Thank you for contacting Aviva — our team will be delighted to help you. "
            f"Is there anything else I can assist with before you go?"
        ),
    }
