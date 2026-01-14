from typing import override
from google.adk.agents import Agent, SequentialAgent
from dotenv import load_dotenv
import datetime
from zoneinfo import ZoneInfo
from google.adk.tools import FunctionTool

import requests
import json


AGENT_MODEL = "gemini-2.5-flash"


def verify_employee_employer(employee_name: str, employer_name: str) -> str:
    """
    Verifies if a specific person is associated with a specific company on LinkedIn.
    Use this to confirm "Shadow Assets" belong to the correct member.
    """
    import requests
    import json

    # Use your Serper or Google API Key
    api_key = "AIzaSyBDABDIrUBUikRx4oTj7E8IxRy2PQsTsOM"
    url = "https://google.serper.dev/search"
    
    # The 'in' path targets individual profiles
    query = f"site:linkedin.com/in \"{employee_name}\" \"{employer_name}\""
    
    payload = json.dumps({"q": query})
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}

    response = requests.post(url, headers=headers, data=payload)
    results = response.json().get('organic', [])

    if not results:
        return f"No LinkedIn profile found matching {employee_name} at {employer_name}."

    # Extracting the first result's info
    match = results[0]
    return f"Verified Match Found: {match.get('title')}\nSnippet: {match.get('snippet')}"

linkedin_tool = FunctionTool(verify_employee_employer)
   
# -- Sequential Agent ---
dormant_account_agent = Agent(
    name="DormantAccountAgent",
    model=AGENT_MODEL,
    #tools=[linkedin_tool],
    description="An agent that searches the internal DB to find out records that are not updated more than 6 months",
    instruction="""
    You are a Financial Agent. You will be given a a source dataset Members_Accounts_E.csv. You will identify dormant accounts:
    - Account that is not updated over 6 months based on last_contribution_date
    """,
    #output_key="dormant_accounts",
)

dormant_remediation_agent = Agent(
    model=AGENT_MODEL,
    name="RemediationAgent",
    description="An agent that searches the employee and employer name in the linked in using the tool provided ",
    instruction="""
    You are a remdiation agent. if the employee name and employer name are matching in the linked in search using the tool provided:
    - Search the employee and employer name for the record
    - If they are not matching,save the record in a remediation_accounts.csv
      
    
    
    """,
    tools=[linkedin_tool]
)

root_agent = SequentialAgent(
    name="DormantPensionsAccount",
    # model=LiteLlm(AGENT_MODEL),#not needed for SequentialAgent
    # model=AGENT_MODEL, #not needed for SequentialAgent
    description="A comprehensive system that identifies 2 dormant pension accounts based on the last contributions, employer checks and remediates if possible.",
    sub_agents=[
        dormant_account_agent,
        dormant_remediation_agent,        
    ],
  
)

