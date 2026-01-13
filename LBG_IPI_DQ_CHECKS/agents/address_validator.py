from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from .tools.AddressValidator import AddressAgent
from .tools.schemas import address_not_found_response
import json
from datetime import datetime
from google.cloud import storage
from dotenv import load_dotenv
import os

load_dotenv(override=True)

def upload_to_gcs(data: dict, bucket_name: str):
    """Helper function to upload JSON data to a GCP Bucket."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        # Create a unique filename based on ID Number and Timestamp
        id_num = data["DetailsFromID"].get("id_number", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        blob_name = f"AddressValidator_DQ_Output/{id_num}_{timestamp}.json"
        
        blob = bucket.blob(blob_name)
        blob.upload_from_string(
            data=json.dumps(data, indent=2),
            content_type='application/json'
        )
        print(f"Successfully uploaded results to gs://{bucket_name}/{blob_name}")
    except Exception as e:
        print(f"GCS Upload Failed: {e}")

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
        "CustomerAddressDQ": address_profile.model_dump()
    }

    # --- GCP BUCKET WRITE ---
    # Set your bucket name here or via environment variable
    BUCKET_NAME = 'lbg-ipi-digitalwallet'
    upload_to_gcs(combined_output, BUCKET_NAME)
    
    return combined_output

address_validator_dq = LlmAgent(
    name="AddressValidator_Agent",
    model="gemini-2.0-flash",
    instruction="""
    You receive the 'extraction_state'.
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