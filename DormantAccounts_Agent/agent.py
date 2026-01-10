from typing import override
from google.adk.agents.llm_agent import Agent
from dotenv import load_dotenv
import datetime
from zoneinfo import ZoneInfo


root_agent = Agent(
    model='gemini-2.5-flash',
    name='DormantAccounts_Agent',
    description='Agent to validate the dormant accounts.',
    instruction='You are a helpful agent who can halp on dormant accounts.'
    #tools=[get_current_time, get_weather]
)
