from google.adk.agents.llm_agent import Agent
from dotenv import load_dotenv
import requests
from tools.AddressValidator import AddressAgent

load_dotenv(override=True)

def search_address(address: str) -> dict:
    """
    Lightweight address validation heuristic.
    """

    addrAgent = AddressAgent(db_path='Data/uk_validation.db')

    keywords = ["street", "st", "road", "rd", "lane", "ln", "avenue", "ave", "postcode", "zip"]

    exists = any(k in address.lower() for k in keywords)

    result = addrAgent.validate(address)
    return result.model_dump_json


root_agent = Agent(
    model="gemini-2.5-flash",
    name="AddressValidator_Agent",
    description="Agent to validate the address provided",
    instruction="""
You validate postal addresses.

Use the search tool to check whether the address exists.
Respond clearly with either:
- Address exists
- Address not found
- Also show me the complete output from the tool
""",
    tools=[search_address],  # ✅ callable = safe
)
