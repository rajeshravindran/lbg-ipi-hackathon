import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from google.genai import types
from google.adk.agents.llm_agent import Agent
from google.adk.tools import ToolContext
from dotenv import load_dotenv

# Ensure this import works based on your folder structure
from .tools.read_image import load_and_ocr_image

load_dotenv(override=True)
SCRIPT_DIR = Path(__file__).parent.resolve()

class IDExtraction(BaseModel):
    full_name: str = Field(description="The full name as it appears on the ID")
    date_of_birth: Optional[str] = Field(None, description="DOB in YYYY-MM-DD or as seen")
    address: Optional[str] = Field(None, description="Full residential address")
    id_number: str = Field(description="The unique identification number")
    issuing_authority: Optional[str] = Field(None)
    is_expired: Optional[bool] = Field(None)    

# FIX: Added 'async' keyword here
async def load_image(path: str, tool_context: ToolContext) -> str:
    """
    Loads an image from the agent's Data/ folder and saves as artifact.
    """
    filename = Path(path).name
    img_path = SCRIPT_DIR / "Data" / filename
    
    if not img_path.exists():
        return f"Error: File not found at {img_path}"

    try:
        image_bytes = img_path.read_bytes()
        mime = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime)

        # This 'await' now works correctly
        await tool_context.save_artifact(filename, image_part)
       
        return f"Success: {filename} loaded. You can now analyze its visual content."
    except Exception as e:
        return f"Error: {str(e)}"

root_agent = Agent(
    name='id_data_extractor_agent',
    model='gemini-2.0-flash',
    description="Extracts information from ID proofs.",
    instruction="""
    1. Use 'load_image' or 'load_and_ocr_image' to get the file.
    2. Extract details including Name, DOB, Address, and ID Number.
    """,
    tools=[load_image, load_and_ocr_image],
)