"""
Root Orchestrator Agent - The main entry point for the Aviva Insurance AI system.

This is the top-level agent that Google ADK discovers and runs. It handles
initial greetings, determines customer type (new vs. existing), performs
authentication, and routes to the appropriate sub-agent.

Architecture:
    root_agent (Orchestrator)
    ├── new_customer_agent (Quote-to-Bind)
    └── existing_customer_agent (Policy Management)
"""

from google.adk.agents import Agent

# Import sub-agents
from .sub_agents.new_customer_agent import new_customer_agent
from .sub_agents.existing_customer_agent import existing_customer_agent

# Import tools available to the root agent
from .tools.customer_tools import authenticate_customer
from .tools.escalation_tools import escalate_to_human

# Import the root agent's system prompt
from .prompts.root_prompt import ROOT_AGENT_PROMPT


# ------------------------------------------------------------------
# Root Agent Definition — the `root_agent` variable is what ADK discovers
# ------------------------------------------------------------------
root_agent = Agent(
    name="aviva_insurance_assistant",
    model="gemini-2.0-flash",
    description=(
        "Aviva Insurance Virtual Assistant — the main orchestrator that "
        "greets customers, determines whether they are new or existing, "
        "authenticates existing customers, and routes them to the "
        "appropriate specialist agent for their needs."
    ),
    instruction=ROOT_AGENT_PROMPT,
    tools=[
        authenticate_customer,
        escalate_to_human,
    ],
    sub_agents=[
        new_customer_agent,
        existing_customer_agent,
    ],
)
