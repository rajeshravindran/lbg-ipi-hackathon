from typing import override
from google.adk.agents.llm_agent import Agent
from dotenv import load_dotenv

load_dotenv(override=True)

def get_current_time(city:str)->dict:
    """
    Returns the current time in a specified city 
    """
    return {
        "status":"success",
        "city":city,
        "time":"10:30 AM"
    }

root_agent = Agent(
    model='gemini-2.5-flash',
    name='AddressValidator_Agent',
    description='Tells the current time in a specified city ',
    instruction='You are a helpful agent which tells the time',
    tools=[get_current_time]
)
