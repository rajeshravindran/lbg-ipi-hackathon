from typing import override
from google.adk.agents.llm_agent import Agent
from dotenv import load_dotenv
import datetime
from zoneinfo import ZoneInfo

load_dotenv(override=True)



root_agent = Agent(
    model='gemini-2.5-flash',
    name='AddressValidator_Agent',
    description='Agent to validate the address provided',
    instruction='You are a helpful agent who will validate the address and flag whether the address is geniune or not',
    tools=[]
)
