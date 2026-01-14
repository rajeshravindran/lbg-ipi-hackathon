import json
import os
import requests
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents import Agent, SequentialAgent, LlmAgent
from google.adk.tools import FunctionTool

# Load environment variables
load_dotenv(override=True)

AGENT_MODEL = "gemini-2.5-flash"

# --- 1. TOOLS ---

def verify_employee_employer(employee_name: str, employer_name: str) -> str:
    """
    Verifies if a specific person is associated with a specific company on LinkedIn.
    This tool uses Serper.dev to search LinkedIn profiles.
    """
    # Note: Serper requires its own API key, usually 'SERPER_API_KEY'
    api_key = os.environ.get("SERPER_API_KEY") 
    if not api_key:
        return "Error: SERPER_API_KEY not found in environment."

    url = "https://google.serper.dev/search"
    
    # Target individual LinkedIn profiles
    query = f"site:linkedin.com/in \"{employee_name}\" \"{employer_name}\""
    
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': api_key, 
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        results = response.json().get('organic', [])

        if not results:
            return f"No LinkedIn profile found matching {employee_name} at {employer_name}."

        match = results[0]
        return f"Verified Match Found: {match.get('title')}\nSnippet: {match.get('snippet')}"
    except Exception as e:
        return f"Search failed: {str(e)}"

linkedin_tool = FunctionTool(verify_employee_employer)

# --- 2. SUB-AGENTS ---

# Agent 1: Filters the CSV data
dormant_account_agent = Agent(
    name="DormantAccountAgent",
    model=AGENT_MODEL,
    description="Identifies dormant accounts (no contribution for >6 months) from the dataset.",
    instruction="""
    You are a Financial Data Analyst. You have access to 'Members_Accounts_E.csv'.
    Today's date is 2026-01-14. 
    
    1. Scan the dataset for members whose 'last_contribution_date' is older than 2025-07-14 (6 months ago).
    2. Focus specifically on those marked 'Missing_Contrib'.
    3. Output ONLY a JSON list of these members with their 'full_name' and 'employer_name'.
    
    Example Output Format:
    [{"full_name": "Linda Berkowitz", "employer_name": "IBM"}, {"full_name": "Samuel Osei", "employer_name": "Intel"}]
    """
)

# Agent 2: Processes the list from Agent 1
dormant_remediation_agent = Agent(
    model=AGENT_MODEL,
    name="RemediationAgent",
    description="Validates the identity and employment of dormant account holders via LinkedIn.",
    instruction="""
    You are a Remediation Agent. You will receive a JSON list of dormant accounts.
    For each account in that list:
    1. Use the 'verify_employee_employer' tool to check if the member still works at that company.
    2. If the tool confirms a match, suggest keeping the record.
    3. If no match is found or if there is a discrepancy, flag it for remediation.
    4. Provide a final summary of all accounts checked.
    """,
    tools=[linkedin_tool]
)

# --- 3. SEQUENTIAL PIPELINE ---

document_pensions_agent = SequentialAgent(
    name="DormantPensionsAccount",
    description="A pipeline to identify dormant accounts and verify them via LinkedIn.",
    sub_agents=[
        dormant_account_agent,
        dormant_remediation_agent,        
    ],
)