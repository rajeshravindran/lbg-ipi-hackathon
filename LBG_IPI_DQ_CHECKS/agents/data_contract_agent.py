import os
from typing import Any, Dict, Optional, Union, List
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from google.adk.agents import LlmAgent
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

# --- 1. THE DATA CONTRACT (FLATTENED FOR ADK COMPATIBILITY) ---
class PolicyDetails(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        populate_by_name=True
    )

    policy_number: str = Field(description="The alphanumeric policy identifier.")
    insured_name: str = Field(description="Full name of policy holder.")
    effective_date: Optional[str] = Field(default=None)
    
    # Allows both float numbers and the placeholder string
    premium_amount: Optional[Union[float, str]] = Field(default=None)
    
    currency: str = Field(default="GBP")
    
    # FIX: Using List[str] is the "Golden Path" for ADK/Gemini compatibility.
    # Custom classes inside Lists often cause the 'Failed to parse parameter' error.
    missing_info: List[str] = Field(
        default_factory=list, 
        description="A list of field names that were missing or 'NOT PROVIDED'."
    )
    other_attributes: List[str] = Field(default_factory=list)

    @field_validator('*', mode='before')
    @classmethod
    def normalize_missing(cls, v: Any) -> Any:
        placeholders = {'n/a', 'na', 'not provided', 'not available', 'none', '', 'null', 'missing'}
        if v is None or (isinstance(v, str) and v.strip().lower() in placeholders):
            return "NOT PROVIDED"
        return v

    @model_validator(mode='after')
    def relocate_missing_info(self) -> 'PolicyDetails':
        """Scans main fields and adds any 'NOT PROVIDED' keys to the missing_info list."""
        check_map = {
            "policy_number": self.policy_number,
            "insured_name": self.insured_name,
            "effective_date": self.effective_date,
            "premium_amount": self.premium_amount
        }
        
        for name, val in check_map.items():
            if val == "NOT PROVIDED":
                if name not in self.missing_info:
                    self.missing_info.append(name)
        return self

# --- 2. THE GCS TOOL ---
def get_policy_document_part(gcs_uri: str) -> types.Part:
    """
    Retrieves a PDF document from Google Cloud Storage for analysis.
    """
    return types.Part.from_uri(
        file_uri=gcs_uri,
        mime_type="application/pdf"
    )

# --- 3. THE AGENT DEFINITION ---
data_contract_agent = LlmAgent(
    name='data_contract_agent',
    description="Extracts structured insurance data from PDFs in GCS.",
    model="gemini-2.0-flash", 
    output_schema=PolicyDetails, 
    instruction="""
    You are an expert insurance data extractor.
    1. Call 'get_policy_document_part' with the GCS URI.
    2. Extract the policy_number, insured_name, effective_date, and premium_amount.
    3. If any field is missing, strictly set its value to "NOT PROVIDED".
    4. Also add the name of any missing field to the 'missing_info' list.
    5. Return the result as a JSON object matching the PolicyDetails schema.
    """,
    tools=[get_policy_document_part]
)