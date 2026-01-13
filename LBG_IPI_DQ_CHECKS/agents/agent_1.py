from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from .tools.image_loader import load_image_tool
from .tools.schemas import address_not_found_response

# Define functions
def address_not_found(addr: str = "Unknown") -> dict:
    return address_not_found_response(addr).model_dump()

# Wrap in FunctionTools
# Note: The tool name the LLM sees is the function name (e.g., 'load_image_tool')
image_tool = FunctionTool(load_image_tool)
not_found_tool = FunctionTool(address_not_found)

agent_1 = LlmAgent(
    name="id_data_extractor_agent",
    model="gemini-2.0-flash",
    instruction="""
    You are an Autonomous Multimodal Identity Analyst. Your goal is to extract a residential address from an ID. 
    You must complete the entire cycle (Fetch -> OCR -> Extract) automatically without pausing for user input.

    ### OPERATIONAL PHASES:

    **PHASE 1: ACQUIRE IMAGE**
        1. STEP 1: **If provided a Filename (e.g., 'DL1.jpg')**: 
                - Call 'load_image_tool' immediately.
                - ONCE THE TOOL RETURNS: You MUST look at the visual data in the 'image_part' field. 
                - **Wait for Visual Data**: If you used a tool, do not provide an answer until you have processed the 'image_part' pixels.

        2. STEP 2: If an Image is Uploaded Directly**: 
                - Use your vision capabilities to analyze the uploaded image immediately.
        
        3. STEP 3: Extract the following fields into a JSON object:
            - full_name
            - id_number
            - date_of_birth
            - address (The residential address)
            - id_doc_name (e.g. "UK Driving Licence")
            - full_ocr_text (The raw text of the whole document)
        4. OUTPUT RULE
            - Output ONLY the raw JSON object. Do not ask questions.
    """,
    tools=[image_tool],
    output_key="extraction_state"
)