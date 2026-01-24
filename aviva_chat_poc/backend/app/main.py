from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from orchestrator import ChatOrchestrator
from openai import OpenAI
from dotenv import load_dotenv
import json

app = FastAPI()

orchestrator = ChatOrchestrator()

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ KEEP THIS ONE:
class ChatInput(BaseModel):
    user_message: str

@app.get("/")
async def health_check():
    return {"status": "ok"}

@app.post("/chat")
async def chat_with_ai(input_data: ChatInput):
    try:
        response = await orchestrator.run(input_data.user_message)
        if isinstance(response, dict):
            return {"bot_response": response.get("bot_response", response.get("hello", "No response"))}
        return {"bot_response": str(response)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))