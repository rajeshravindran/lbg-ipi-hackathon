import io
import pypdf # Make sure to pip install pypdf
from typing import Literal
from pydantic import BaseModel, Field
from datetime import datetime
from dotenv import load_dotenv

# Corrected Imports for Gemini ADK
from google.adk.tools import ToolContext, function_tool as tool
from google.adk.agents.llm_agent import  Agent 

load_dotenv(override=True)

class PolicyDetails(BaseModel):
    """Structured data extracted from an insurance policy document."""
    policy_number: str = Field(description="The unique alphanumeric policy identifier.")
    insured_name: str = Field(description="The full name of the policy holder.")
    effective_date: str = Field(description="The policy start date in YYYY-MM-DD format.")
    premium_amount: float = Field(description="The annual premium amount as a floating-point number.")
    currency: Literal["GBP", "EUR", "USD"] = Field(description="The currency of the premium amount.")

def parse_pdf_content() -> PolicyDetails:
    return PolicyDetails (
            policy_number='123',
            insured_name='NAME',
            effective_date=str(datetime.now()),
            premium_amount='100',
            currency='GBP'
        )

# Define the agent object for 'adk run'
root_agent = Agent(
    name="policy_parser_agent",
    model="gemini-2.5-flash", 
    description="Agent to validate the address provided",
    instruction="""
        You are an expert insurance policy data extraction assistant. 
        Use the parse_pdf_content tool to read uploaded files. 
        Extract the policy details and return them strictly as structured data.
    """,
    tools=[parse_pdf_content],
)