import asyncio
import pytesseract
from PIL import Image
from pathlib import Path

# Use the correct import for your environment's types
# If using Gemini/Vertex, this is typically: 
# from google.cloud.aiplatform_v1beta1 import types

# 1. FIX PATH RESOLUTION
# Since read_image.py is in 'tools/', .parent.parent gets us to 'id_data_extractor_agent/'
SCRIPT_DIR = Path(__file__).parent.parent 

print(SCRIPT_DIR)

async def load_and_ocr_image(path: str, tool_context) -> str:
    """
    Loads an image and extracts text via OCR.
    """
    filename = Path(path).name
    # Search in the Data folder relative to the project root
    img_path = SCRIPT_DIR / "Data" / filename
    
    if not img_path.exists():
        return f"Error: File not found at {img_path}"

    try:
        # OCR Processing
        with Image.open(img_path) as img:
            img = img.convert('L')
            img = img.point(lambda x: 0 if x < 140 else 255, '1')
            extracted_text = pytesseract.image_to_string(img, config='--psm 3')

        # Artifact Saving (only if tool_context is provided)
        if tool_context:
            image_bytes = img_path.read_bytes()
            mime = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"
            # Note: Ensure 'types' is imported based on your specific SDK
            # image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime)
            # await tool_context.save_artifact(filename, image_part)

        if not extracted_text.strip():
            return f"Success: {filename} loaded, but no text was detected."

        return f"Success: {filename} OCR Result:\n\n{extracted_text}"

    except Exception as e:
        return f"Error during OCR processing: {str(e)}"

# 2. FIX THE CALLING LOGIC
if __name__ == "__main__":
    # Mocking tool_context for local testing
    class MockContext:
        async def save_artifact(self, name, part): pass

    async def main():
        # Pass the filename and the context object
        ctx = MockContext()
        result = await load_and_ocr_image('DL2.png', ctx)
        print(result)

    asyncio.run(main())

    