"""
Existing Customer Agent - Handles policy management for authenticated customers.

This agent serves as a personal concierge for existing policyholders,
providing services like mid-term adjustments, renewals, cancellation
retention, document retrieval, and proactive recommendations.
"""

from google.adk.agents import Agent

# Import tools used by this agent
from ..tools.customer_tools import get_customer_profile
from ..tools.policy_tools import get_policy, list_customer_policies, update_policy, cancel_policy
from ..tools.search_tools import search_policies, search_claims
from ..tools.comparison_tools import compare_with_providers
from ..tools.suggestion_tools import get_suggestions, get_cross_sell_suggestions
from ..tools.management_tools import (
    process_mta,
    process_renewal,
    get_retention_offers,
    get_policy_documents,
    update_coverage,
)
from ..tools.escalation_tools import escalate_to_human
from ..tools.purchase_tools import generate_quote, process_purchase
from ..prompts.existing_customer_prompt import EXISTING_CUSTOMER_PROMPT


# ------------------------------------------------------------------
# Existing Customer Sub-Agent Definition
# ------------------------------------------------------------------
existing_customer_agent = Agent(
    name="existing_customer_agent",
    model="gemini-2.0-flash",
    description=(
        "Personal concierge agent for authenticated existing Aviva customers. "
        "Manages all policy operations including viewing policies, mid-term "
        "adjustments (address change, add driver, vehicle change), renewals, "
        "cancellation with retention offers, coverage changes, document "
        "retrieval, claims enquiries, and proactive policy suggestions."
    ),
    instruction=EXISTING_CUSTOMER_PROMPT,
    tools=[
        get_customer_profile,
        get_policy,
        list_customer_policies,
        update_policy,
        cancel_policy,
        search_policies,
        search_claims,
        compare_with_providers,
        get_suggestions,
        get_cross_sell_suggestions,
        process_mta,
        process_renewal,
        get_retention_offers,
        get_policy_documents,
        update_coverage,
        generate_quote,
        process_purchase,
        escalate_to_human,
    ],
)
