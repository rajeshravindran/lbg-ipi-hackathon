from pydantic import BaseModel, Field
from typing import List, Optional

# Your exact schema
class CustomerAddressProfile(BaseModel):
    is_valid: bool
    standardized_address: str
    classification: str = Field(description="RESIDENTIAL, BUSINESS, or UNKNOWN")
    
    populated_place: Optional[str] = Field(None, description="The Town or City associated with the address")
    district_borough: Optional[str] = Field(None, description="The Local Authority District or London Borough")
    county: Optional[str] = Field(None, description="The County or Unitary Authority")
    
    risk_score: int = Field(ge=0, le=100)
    risk_flags: List[str]
    confidence_level: str
    provider_metadata: dict