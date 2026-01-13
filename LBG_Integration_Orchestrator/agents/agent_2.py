from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from .tools.AddressValidator import AddressAgent
from .tools.schemas import address_not_found_response
import json

def verify_address_logic(address: str) -> dict:
    # If agent_1 already returned a 'not found' JSON, parse and return it
    if "ADDRESS COULD NOT BE PARSED" in address or '"is_valid": false' in address:
        try:
            return json.loads(address)
        except:
            pass # Continue to validation if parsing fails

    agent = AddressAgent(db_path="Data/uk_validation.db")
    result = agent.validate(address)
    return result.model_dump()

def validate_and_unify(extraction_state: dict) -> dict:
    # Ensure extraction_state is a dict
    data = extraction_state if isinstance(extraction_state, dict) else json.loads(extraction_state)
    
    address_to_verify = data.get("address")
    
    # CRITICAL FIX: Handle None or Empty strings before calling the validator
    if not address_to_verify or str(address_to_verify).strip().lower() in ["none", "unknown", ""]:
        address_profile = address_not_found_response(raw_input="No address extracted")
    else:
        try:
            validator = AddressAgent(db_path="Data/uk_validation.db")
            address_profile = validator.validate(str(address_to_verify))
        except Exception as e:
            address_profile = address_not_found_response(raw_input=str(address_to_verify))

    # Combine into your FinalValidationResponse structure
    combined_output = {
        "DetailsFromID": {
            "full_name": data.get("full_name", "Unknown"),
            "id_number": data.get("id_number", "Unknown"),
            "date_of_birth": data.get("date_of_birth"),
            "address": address_to_verify,
            "id_doc_name": data.get("id_doc_name", "Unknown")
        },
        "CustomerAddressProfile": address_profile.model_dump()
    }
    
    return combined_output

agent_2 = LlmAgent(
    name="AddressValidator_Agent",
    model="gemini-2.0-flash",
    instruction="""
    You receive the 'extraction_state' from Agent 1.
    Call the 'validate_and_unify' tool to perform database validation and merge the results into the final schema.
    Return the final JSON object.
    """,
    tools=[FunctionTool(validate_and_unify)]
)

"""
agent_2 = LlmAgent(
    name="AddressValidator_Agent",
    model="gemini-2.0-flash",
    instruction=
        You receive the 'extracted_address' from the previous agent.
        1. If the input is already a JSON error structure (is_valid: false), return it exactly as is.
        2. If the input is a physical address string, call 'verify_address_logic' to validate it against the database.
        3. Return the final JSON schema.
        ,
    tools=[FunctionTool(verify_address_logic)]
)
"""