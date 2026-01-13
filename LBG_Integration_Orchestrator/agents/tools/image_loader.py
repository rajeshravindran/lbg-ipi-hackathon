from pathlib import Path
from google.genai import types

def load_image_tool(path: str) -> dict:
    p = Path(path)
    if not p.is_absolute():
        # Adjust this path to where your images actually sit relative to this file
        img_dir = Path(__file__).parent.parent / "Data" / "images"
        img_path = img_dir / p.name
    else:
        img_path = p

    print(img_path)

    if not img_path.exists():
        return {"error": f"Image file not found: {img_path}"}
    
    # Returning the metadata so the LLM knows the image is 'attached'
    return {"status": "Success", "filename": img_path.name, "path": str(img_path)}