from pydantic import BaseModel, Field
from typing import List, Optional

class DetailsFromID(BaseModel):
    full_name: str
    id_number: str
    date_of_birth: str | None = None
    address: str | None = None
    id_doc_name: str

class CustomerAddressDQ(BaseModel):
    is_valid: bool
    standardized_address: str
    classification: str = Field(description="RESIDENTIAL, BUSINESS, or UNKNOWN")
    is_duplicate: bool
    
    populated_place: Optional[str] = Field(None, description="The Town or City associated with the address")
    district_borough: Optional[str] = Field(None, description="The Local Authority District or London Borough")
    county: Optional[str] = Field(None, description="The County or Unitary Authority")
    
    risk_score: int = Field(ge=0, le=100)
    risk_flags: List[str]
    confidence_level: str
    provider_metadata: dict

class FinalValidationResponse(BaseModel):
    DetailsFromID: DetailsFromID
    CustomerAddressDQ: CustomerAddressDQ

def address_not_found_response(raw_input: str=None, country: str = None) -> CustomerAddressDQ:
    return CustomerAddressDQ(
        is_valid=False,
        standardized_address=f"{raw_input}, UNKNOWN",
        classification="UNKNOWN",
        is_duplicate=False, # Changed to False for clarity on a new lookup
        populated_place=None,
        district_borough=None,
        county=None,
        risk_score=100,
        risk_flags=["ADDRESS COULD NOT BE PARSED"],
        confidence_level="LOW",
        provider_metadata={
            "country": country or "UK",
            "local_type": "N/A",
            "os_id": None
        }
    )