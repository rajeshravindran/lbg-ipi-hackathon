"""
New Customer Agent - Handles the quote-to-bind journey for new customers.

This agent guides prospective customers through getting an insurance quote
and purchasing a policy using natural conversation. Covers both auto and
property insurance types.
"""

from google.adk.agents import Agent

# Import tools used by this agent
from ..tools.vehicle_tools import lookup_vehicle_by_vrn
from ..tools.purchase_tools import generate_quote, process_purchase
from ..tools.comparison_tools import compare_with_providers
from ..tools.suggestion_tools import get_suggestions
from ..tools.customer_tools import create_customer
from ..prompts.new_customer_prompt import NEW_CUSTOMER_PROMPT


# ------------------------------------------------------------------
# New Customer Sub-Agent Definition
# ------------------------------------------------------------------
new_customer_agent = Agent(
    name="new_customer_agent",
    model="gemini-2.0-flash",
    description=(
        "Specialist agent for new customers seeking insurance quotes. "
        "Handles the complete quote-to-bind journey for both car and home "
        "insurance, including vehicle lookup, quote generation, provider "
        "comparison, and policy purchase."
    ),
    instruction=NEW_CUSTOMER_PROMPT,
    tools=[
        lookup_vehicle_by_vrn,
        generate_quote,
        process_purchase,
        compare_with_providers,
        get_suggestions,
        create_customer,
    ],
)
