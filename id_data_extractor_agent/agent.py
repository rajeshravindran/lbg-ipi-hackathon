import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from google.genai import types
from google.adk.agents.llm_agent import Agent
from google.adk.tools import ToolContext
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# --- PATH SETUP ---
SCRIPT_DIR = Path(__file__).parent.resolve()

# --- 1. DEFINE STRUCTURED OUTPUT MODEL ---
# This replaces the dictionary schema that caused the Pydantic error
class IDExtraction(BaseModel):
    full_name: str = Field(description="The full name as it appears on the ID")
    date_of_birth: Optional[str] = Field(None, description="DOB in YYYY-MM-DD or as seen")
    address: Optional[str] = Field(None, description="Full residential address")
    id_number: str = Field(description="The unique identification number")
    issuing_authority: Optional[str] = Field(None)
    is_expired: Optional[bool] = Field(None)

# --- 2. ASYNC TOOL ---
async def load_image(path: str, tool_context: ToolContext) -> str:
    """
    Loads an image from the agent's Data/images/ folder and saves as artifact.
    """
    filename = Path(path).name
    # Path resolution based on your specific directory structure
    img_path = SCRIPT_DIR / "Data" / filename
    
    if not img_path.exists():
        # Fallback if 'images' subfolder isn't used
        img_path = SCRIPT_DIR / "id_data_extractor_agent" / "Data" / filename

    print(img_path)

    if not img_path.exists():
        return f"Error: File not found at {img_path}"

    try:
        image_bytes = img_path.read_bytes()
        mime = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime)

        # Await the artifact saving
        await tool_context.save_artifact(filename, image_part)
       
        return f"Success: {filename} loaded. You can now analyze its visual content."
    except Exception as e:
        return f"Error: {str(e)}"

# --- 3. AGENT SETUP ---
# If your version of ADK doesn't support 'response_schema', 
# we use the Pydantic model inside the 'outputs' or simply in instructions.
root_agent = Agent(
    name='id_data_extractor_agent',
    model='gemini-2.5-flash',
    description="A helper agent to extract the information from the ID proof submitted by the user which will be used for validation",
    instruction="""
    FLOW:
    1. Call 'load_image' with the filename the user provides (e.g., 'DL1.jpg').
    2. Once successful, visually analyze the loaded image.
    3. Extract the following details from the ID proof:
        1. Name
        2. Date of Birth
        3. Address
        4. ID Number
        5. Issuing Authority
        6. Validity Period (if applicable)
    Ensure that all extracted information is accurate and complete.
    """,
    tools=[load_image],
    )