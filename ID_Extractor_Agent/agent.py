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

async def clear_history(tool_context: ToolContext) -> str:
    try:
        # Access the underlying message history in the ADK session
        # This removes the accumulated image tokens from previous turns
        if hasattr(tool_context, 'parent_context') and hasattr(tool_context.parent_context, 'messages'):
            tool_context.parent_context.messages = []
            return "Success: Conversation history cleared. Tokens reset."
        return "Warning: Could not find history to clear, but proceeding."
    except Exception as e:
        return f"Error clearing history: {str(e)}"

# FIX: Added 'async' keyword here
async def load_image(path: str, tool_context: ToolContext) -> types.Part:
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
        return image_part
        #return f"Success: {filename} loaded. You can now analyze its visual content."
    except Exception as e:
        return f"Error: {str(e)}"

root_agent = Agent(
    name='ID_Extractor_Agent',
    model='gemini-2.0-flash',
    description="Extracts information from ID proofs.",
    instruction="""
    You are an ID validation expert. 
    1. When a user provides a filename, call 'load_image' immediately using that filename as the 'path'.
    2. Once you receive the image data, examine it carefully to extract details.
    3. If visual details are unclear, call 'load_and_ocr_image' for text assistance.
    4. Cross-reference visual data with OCR text. If they differ, prefer the MRZ (bottom text) for Passports.
    4. Extract: Full Name, Date of Birth (YYYY-MM-DD), Address, and ID Number.
    5. Use 'clear_history' if you encounter a token limit error or after every 2 extractions.
    6. Provide the final output strictly in this JSON format:
    {IDExtraction.model_json_schema()}
    """,
    tools=[load_image, load_and_ocr_image, clear_history],
)