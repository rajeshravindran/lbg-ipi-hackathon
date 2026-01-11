from google.adk.agents.llm_agent import Agent
from dotenv import load_dotenv
from .tools.AddressValidator import AddressAgent
import os

load_dotenv(override=True)

def search_address(address: str) -> dict:
    """
    Lightweight address validation heuristic.
    """

    addrAgent = AddressAgent(db_path='Data/uk_validation.db')

    keywords = ["street", "st", "road", "rd", "lane", "ln", "avenue", "ave", "postcode", "zip"]

    exists = any(k in address.lower() for k in keywords)

    result = addrAgent.validate(address)
    return result.model_dump_json()



current_dir = os.path.dirname(os.path.abspath(__file__))
prompt_path = os.path.join(current_dir, "prompts.txt")
with open(prompt_path, "r") as f:
    agent_instructions = f.read()

root_agent = Agent(
    model="gemini-2.5-flash",
    name="AddressValidator_Agent",
    description="Agent to validate the address provided",
    instruction=agent_instructions,
    tools=[search_address], 
)
