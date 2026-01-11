import os
from typing import override
from google.maps import addressvalidation_v1
from google.type import postal_address_pb2
from schemas import CustomerAddressProfile
from dotenv import load_dotenv

from google.api_core.client_options import ClientOptions

load_dotenv(override=True)

class AddressValidator:
    def __init__(self):
        # Set environment variable for the Google SDK
        options = ClientOptions(api_key=os.getenv('GOOGLE_MAP_API'))
        self.client = addressvalidation_v1.AddressValidationClient(client_options=options)

    def validate(self, raw_address: str, region_code: str = "US") -> CustomerAddressProfile:
        # Prepare the request
        address = postal_address_pb2.PostalAddress(
            address_lines=[raw_address],
            region_code=region_code
        )
        request = addressvalidation_v1.ValidateAddressRequest(address=address)
        
        # Call Google API
        response = self.client.validate_address(request)
        result = response.result
        verdict = result.verdict
        
        # 1. Standardization & Classification Logic
        standardized = result.address.formatted_address
        metadata = result.metadata
        
        # Classification: Residential vs Business
        business = metadata.business
        residential = metadata.residential
        address_type = "BUSINESS" if business else "RESIDENTIAL" if residential else "UNKNOWN"

        # 2. Risk Scoring Logic
        risk_score = 0
        flags = []

        if verdict.validation_granularity == "OTHER":
            risk_score += 50
            flags.append("LOW_PRECISION")
        
        if not verdict.address_complete:
            risk_score += 30
            flags.append("INCOMPLETE_ADDRESS")

        if metadata.po_box:
            risk_score += 20
            flags.append("PO_BOX")

        # Return Pydantic object
        return CustomerAddressProfile(
            is_valid=verdict.address_complete,
            standardized_address=standardized,
            classification=address_type,
            risk_score=min(risk_score, 100),
            flags=flags,
            granularity=str(verdict.validation_granularity).split('.')[-1],
            plus_code=result.geocode.plus_code.global_code if result.geocode.plus_code else None
        )

        def calculate_risk_score(self, data, internal_blacklist):
            score = 0
        factors = []
        
        # 1. Check Validity
        if not google_data.verdict.address_complete:
            score += 40
            factors.append("INCOMPLETE_ADDRESS")
            
        # 2. Check Type (Step 2 in your list)
        if google_data.metadata.po_box:
            score += 30
            factors.append("PO_BOX_DETECTION")
            
        # 3. Internal Check (Step 3 in your list)
        formatted = google_data.address.formatted_address
        if formatted in internal_blacklist:
            score = 100
            factors.append("INTERNAL_HIGH_RISK_MATCH")
            
        return min(score, 100), factors


if __name__=="main":
    validator = AddressValidator()
    # Test with a standard address
    raw_input = "1600 Amphitheatre Pkwy, Mountain View, CA"
    try:
        report = validator.validate(raw_input)
        print(report.model_dump_json(indent=2))
    except Exception as e:
        print(f"Error during validation: {e}")