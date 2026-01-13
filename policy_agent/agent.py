# In your agent.py code
from google import genai
from google.genai import types

client = genai.Client(
    vertexai=True,
    project="project-244-295208", # or os.environ.get("GOOGLE_CLOUD_PROJECT")
    location="us-central1"        # or os.environ.get("GOOGLE_CLOUD_LOCATION")
)

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any, Dict, Optional, Union
from google.adk.tools import ToolContext 
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

def extract_policy_from_gcs(gcs_uri: str='gs://lbg-ipi-digitalwallet/data_contract/Policy_001_Standard_Auto_Insurance.pdf', tool_context: ToolContext) -> PolicyDetails:
    """
    Reads a PDF from GCS and extracts structured policy data.
    Args:
        gcs_uri: The Cloud Storage path (e.g., 'gs://your-bucket/policy.pdf')
    """
    # 1. Define the PDF part from the URI
    pdf_file = types.Part.from_uri(
        file_uri=gcs_uri,
        mime_type="application/pdf"
    )

    # 2. Call the model using the pre-initialized 'client'
    # The SDK will use the model assigned to the agent
    response = client.models.generate_content(
        model="gemini-2.0-flash", 
        contents=[pdf_file, "Extract policy details from this document."],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PolicyDetails # Enforce your Pydantic schema
        )
    )

    # 3. Use the skip_summarization flag for raw tool output
    tool_context.actions.skip_summarization = True
    
    # Return the validated object; ADK will handle the 'PolicyDetails' formatting
    return response.parsed 

root_agent = Agent(
    name="policy_parser_agent",
    model="gemini-2.0-flash", 
    output_schema=PolicyDetails, 
    instruction="Extract data from GCS-stored PDFs. Use the provided tool to access files.",
    tools=[extract_policy_from_gcs], # Added the GCS tool
)