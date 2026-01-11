from pydantic import BaseModel, Field
from typing import List, Optional

# Your exact schema
class CustomerAddressProfile(BaseModel):
    is_valid: bool
    standardized_address: str
    classification: str = Field(description="RESIDENTIAL, BUSINESS, or UNKNOWN")
    risk_score: int = Field(ge=0, le=100)
    risk_flags: List[str]
    confidence_level: str
    provider_metadata: dict