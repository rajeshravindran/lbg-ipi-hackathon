# In your agent.py code
from google import genai

client = genai.Client(
    vertexai=True,
    project="project-244-295208", # or os.environ.get("GOOGLE_CLOUD_PROJECT")
    location="us-central1"        # or os.environ.get("GOOGLE_CLOUD_LOCATION")
)

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any, Dict, Optional, Union
from google.adk.tools import ToolContext # Ensure this is imported
from google.adk.agents.llm_agent import Agent

class PolicyDetails(BaseModel):
    # Main Data
    policy_number: str = Field(description="The alphanumeric policy identifier.")
    insured_name: str = Field(description="Full name of policy holder.")
    effective_date: Optional[str] = Field(default=None)
    premium_amount: Optional[float] = Field(default=None)
    currency: str = Field(default="GBP")

    # Separation Objects
    missing_info: Dict[str, str] = Field(default_factory=dict)
    other_attributes: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('*', mode='before')
    @classmethod
    def normalize_missing(cls, v: Any) -> Any:
        placeholders = {'n/a', 'na', 'not provided', 'not available', 'none', '', 'null'}
        if v is None or (isinstance(v, str) and v.strip().lower() in placeholders):
            return "NOT PROVIDED"
        return v

    @model_validator(mode='after')
    def relocate_missing_info(self) -> 'PolicyDetails':
        """Physically moves 'NOT PROVIDED' fields to the missing_info object."""
        for f in ["effective_date", "premium_amount"]:
            if getattr(self, f) == "NOT PROVIDED":
                self.missing_info[f] = "NOT PROVIDED"
                setattr(self, f, None)
        
        # Check other_attributes for missing entries
        temp_other = self.other_attributes.copy()
        for k, v in temp_other.items():
            if v == "NOT PROVIDED":
                self.missing_info[k] = "NOT PROVIDED"
                del self.other_attributes[k]
        return self

def parse_pdf_content(details: PolicyDetails, tool_context: ToolContext) -> dict:
    """
    Extracts policy data and physically separates missing info.
    """
    # 1. CRITICAL: Tells ADK to return the raw tool result without AI summarization
    tool_context.actions.skip_summarization = True
    
    # Return the already-separated dictionary (the model_validator moved the fields)
    return details.model_dump(exclude_none=True)

root_agent = Agent(
    name="policy_parser_agent",
    model="gemini-2.0-flash", 
    # 2. CRITICAL: Enforce the schema on the final response so the separator runs
    output_schema=PolicyDetails, 
    instruction="""
        You are a data extraction engine. 
        - Extract all fields from the PDF.
        - If a field is missing, blank, or 'N/A', you MUST set its value to 'NOT PROVIDED'.
        - Extra fields (Address, Deductible) MUST go into 'other_attributes'.
        - DO NOT summarize. Output the raw data structured by your tools.
    """,
    tools=[parse_pdf_content],
)