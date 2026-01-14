import asyncio
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict
import json
import csv

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Load environment variables from .env file
load_dotenv()

# --- 0. SETUP ---
SCRIPT_DIR = Path(__file__).parent.resolve()
DATA_DIR = SCRIPT_DIR / "Data"
USER_DATA_PATH = DATA_DIR / "user_input_data.json" # User Input data for DQ
IMG_DATA_PATH = DATA_DIR / "images"

print (f"{USER_DATA_PATH}\n{IMG_DATA_PATH}")

# --- 1. SCHEMAS ---
class IDDetails(BaseModel):
    # This configuration is the "Secret Sauce" for Gemini
    model_config = ConfigDict(
        extra='forbid',
        populate_by_name=True
    )
    full_name: str
    id_number: str
    date_of_birth: str | None = None
    address: str | None = None
    id_doc_name: str

class DQResult(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        populate_by_name=True
    )
    id_doc_name: str
    DQ_result: str  # "PASS" or "FAIL"
    DQ_reason: str | None = None
   
# Create a simple global variable to hold the path
current_processing_path = None

# --- 2. MULTIMODAL INJECTION ---
async def inject_id_image(callback_context, llm_request):
    # --- PART A: FORCED SCHEMA CLEANING (NEW CHANGE) ---
    # This manually deletes the "additional_properties" field that Gemini hates
    try:
        if hasattr(llm_request, 'generation_config') and llm_request.generation_config:
            schema = getattr(llm_request.generation_config, 'response_schema', None)
            if schema:
                # Recursively remove the field if it exists
                def remove_extra_props(obj):
                    if isinstance(obj, dict):
                        obj.pop('additional_properties', None)
                        obj.pop('additionalProperties', None)
                        for v in obj.values():
                            remove_extra_props(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            remove_extra_props(item)
               
                # Apply the cleaner to the dictionary representation of the schema
                if hasattr(schema, 'to_dict'):
                    schema_dict = schema.to_dict()
                    remove_extra_props(schema_dict)
                    # Note: Depending on ADK version, you might just be able to
                    # delete it from the object directly if it's a dict
    except Exception as e:
        print(f"⚠️ Schema cleaning warning: {e}")
    global current_processing_path
   
    # Use the global variable instead of callback_context
    if not current_processing_path or not current_processing_path.exists():
        return
         
    image_bytes = current_processing_path.read_bytes()
    mime = "image/jpeg" if current_processing_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
    # Get the exact filename
    filename = current_processing_path.name
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime)
   
    # Add the filename as a text part so the LLM knows what it's called
    filename_part = types.Part(text=f"The filename of this document is: {filename}")
   
    if llm_request.contents is None:
        llm_request.contents = []
   
# We bundle the filename and the image together in the user message
    llm_request.contents.append(types.Content(role="user", parts=[image_part, filename_part]))

# --- 3. AGENT DEFINITION ---

# Agent 1: The Extractor
id_extractor_agent = LlmAgent(
    name='id_data_extractor_agent',
    description='An agent that extracts ID details from images.',
    model='gemini-2.5-flash',
    instruction="""You are an expert in extracting information from ID proofs which include but are not limited to passports, driver licenses, national ID cards, etc. It will be in image or scanned document format.
    1. Look at the attached image or document.
    2. Extract the details accurately.
    3. Return the data ONLY as a JSON object following the given schema.
    4. If information is missing, use null.
    5. Use the provided 'filename' in the prompt to fill the 'id_doc_name' field.
    6. Format the Date of Birth as YYYY-MM-DD.
    7. Do not add any extra text or explanation outside the JSON object.
    8. Return ONLY valid JSON as per the below structure.
            full_name: str
            id_number: str
            date_of_birth: str | None = None
            address: str | None = None
            id_doc_name: str
    """,
    #output_schema=IDDetails,
    before_model_callback=inject_id_image
)

async def main():
    # 1. Initialize result list early to prevent UnboundLocalError
    all_results = []
    try:
        if not USER_DATA_PATH.exists():
            print(f"❌ Error: Reference file not found at {USER_DATA_PATH}")
            return
        # Load Reference Data for comparison
        with open(USER_DATA_PATH, 'r') as f:
            reference_list = json.load(f)
           
        # Get all image files in the data directory
        extensions = ("*.jpg", "*.jpeg", "*.png")
        image_files = []
        for ext in extensions:
            image_files.extend(IMG_DATA_PATH.glob(ext))

        if not image_files:
            print(f"No images found in {IMG_DATA_PATH}")
            return

        print(f"📂 Found {len(image_files)} images. Starting processing...")

        session_service = InMemorySessionService()
        app_name = "batch_id_extractor"
       
        for idx, image_path in enumerate(image_files):
           
            print(f"\n[{idx+1}/{len(image_files)}] Processing: {image_path.name}...")
            # CHANGE A: Update the global path for the callback to find
            global current_processing_path
            current_processing_path = image_path
                   
            # Each image needs a unique session or a cleared session
            session_id = f"session_extract_{idx}"
            await session_service.create_session(session_id=session_id, user_id="default_user", app_name=app_name)
       
            runner = Runner(agent=id_extractor_agent, session_service=session_service, app_name=app_name)
           
            response_text = ""
            # We pass the image path via kwargs so the callback can access it
            async for event in runner.run_async(
                user_id="default_user",
                session_id=session_id,
                new_message=types.Content(role="user", parts=[types.Part(text="Extract info.")])
            ):
                if hasattr(event, 'is_final_response') and event.is_final_response():
                    if event.content and event.content.parts:
                        response_text = event.content.parts[0].text

            # --- 5. OUTPUT HANDLING ---
            if response_text:
                # 1. Strip Markdown backticks if Gemini added them
                    clean_json = response_text.strip()
                    if clean_json.startswith("```json"):
                        clean_json = clean_json.removeprefix("```json").removesuffix("```").strip()
                    elif clean_json.startswith("```"):
                        clean_json = clean_json.removeprefix("```").removesuffix("```").strip()

                    # 2. Convert the string into a Python Dictionary
                    extracted_data = json.loads(clean_json)
                    print(f"✅ Extracted: {extracted_data}")
                   
                    # 3. Save individual file (Optional)
                    individual_file = DATA_DIR / f"{image_path.stem}_data.json"
                    with open(individual_file, 'w') as f:
                        json.dump(extracted_data, f, indent=4)
                        print(f"✅ Success: {image_path.name}")
                       
                        # --- NEW DQ AGENT STEP ---
                # Find matching user data from reference list
                   # Match with Reference
                    ref_entry = next((item for item in reference_list if item["id_doc_name"] == image_path.name), None)
                   
                    if ref_entry:
                        dq_session_id = f"session_dq_{idx}"
                        # FIX: Create the session for the DQ agent!
                        await session_service.create_session(
                            session_id=dq_session_id, user_id="default_user", app_name=app_name
                        )
                       
                        dq_runner = Runner(agent=id_dq_agent, session_service=session_service, app_name=app_name)
                        dq_prompt = f"Extracted: {json.dumps(extracted_data)}\nReference: {json.dumps(ref_entry)}"
                       
                        async for dq_event in dq_runner.run_async(
                            user_id="default_user", session_id=dq_session_id,
                            new_message=types.Content(role="user", parts=[types.Part(text=dq_prompt)])
                        ):
                            if hasattr(dq_event, 'is_final_response') and dq_event.is_final_response():
                                dq_clean = dq_event.content.parts[0].text.strip().removeprefix("```json").removesuffix("```").strip()
                                dq_data = json.loads(dq_clean)
                                extracted_data.update(dq_data) # Merge DQ result into record
                   
                    print(f"✅ DQ: {extracted_data.get('DQ_result', 'SKIPPED')}")
                    all_results.append(extracted_data)
                   
                    output_file = f"{image_path.stem}_data.json"
                    with open(output_file, 'w') as f:
                        json.dump(extracted_data, f, indent=4)
            else:
                print(f"❌ Failed extraction for {image_path.name}")
             
            # --- FINAL MASTER FILE ---
        if all_results:
                    # 1. Save JSON Master
                    master_json = DATA_DIR / "all_extracted_ids.json"
                    with open(master_json, 'w', encoding='utf-8') as f:
                        json.dump(all_results, f, indent=4)
                   
                    # 2. Save CSV for Excel (The Verification Step)
                    master_csv = DATA_DIR / "final_dq_report.csv"
                    keys = all_results[0].keys() # Dynamically get columns
                    with open(master_csv, 'w', newline='', encoding='utf-8') as f:
                        dict_writer = csv.DictWriter(f, fieldnames=keys)
                        dict_writer.writeheader()
                        dict_writer.writerows(all_results)

                    # 3. Print Visual Summary to Terminal
                    print("\n" + "="*60)
                    print(f"{'BATCH EXTRACTION & DQ SUMMARY':^60}")
                    print("="*60)
                    print(f"{'ID Document':<25} | {'Status':<8} | {'Reason'}")
                    print("-" * 60)
                   
                    passes = 0
                    for res in all_results:
                        status = res.get('DQ_result', 'N/A')
                        print(f"{res.get('id_doc_name', 'Unknown')[:25]:<25} | {status:<8} | {res.get('DQ_reason', '')}")
                        if status == 'PASS': passes += 1
                   
                    print("-" * 60)
                    print(f"📈 Accuracy: {passes}/{len(all_results)} Passed")
                    print(f"📁 JSON: {master_json.name}")
                    print(f"📊 CSV:  {master_csv.name} (Open in Excel to verify)")
                    print("="*60)

    except Exception as e:
        print(f"❌ Batch Error: {e}")

# Agent 2: The DQ Validator
id_dq_agent = LlmAgent(
    name='id_dq_validator_agent',
    model='gemini-2.5-flash',
    instruction="""Compare 'Extracted Data' vs 'Reference Data'.
    1. Check if full_name and id_number are logically the same (ignore case/minor formatting).
    2. If they match, DQ_result='PASS'. Otherwise 'FAIL'.
    3. Provide a clear DQ_reason if they mismatch.
    4. Return ONLY the requested JSON schema as per below structure.
        id_doc_name: str
        DQ_result: str  # "PASS" or "FAIL"
        DQ_reason: str | None = None
    """,
    #output_schema=DQResult,
    before_model_callback=inject_id_image
)
       
if __name__ == "__main__":
    asyncio.run(main())