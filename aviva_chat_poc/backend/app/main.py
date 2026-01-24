import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

app = FastAPI()

client = OpenAI(
    base_url='https://generativelanguage.googleapis.com/v1beta/openai/',
    api_key=os.getenv("GOOGLE_API_KEY")
)

origins = [
    "http://localhost:5173",  # Default Vite React dev server
    "http://localhost:3000",  # Common Create React App dev server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, etc.)
    allow_headers=["*"], # Allow all headers
)

class ChatInput(BaseModel):
    user_message: str

@app.get("/")
async def health_check():
    """A simple endpoint to confirm the server is running."""
    return {"status": "ok"}

@app.post("/chat")
async def chat_with_ai(input_data: ChatInput):
    """The main endpoint to handle chat interactions."""
    
    try:
        completion = client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": input_data.user_message},
            ],
        )
        # Extract and return the AI's response
        bot_response = completion.choices[0].message.content
        return {"bot_response": bot_response}
    except Exception as e:
        # Properly handle potential API errors
        raise HTTPException(status_code=500, detail=str(e))