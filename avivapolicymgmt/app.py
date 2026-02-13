"""
Aviva Insurance Policy Management - FastAPI Application Server.

Serves the Aviva-styled web UI and provides the chat API endpoint
that bridges the frontend with the Google ADK agent system.

Usage:
    python app.py
    # or
    uvicorn app:app --reload --port 8000
"""

import os
import uuid
import json
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Load environment variables (.env file with GOOGLE_API_KEY)
load_dotenv()

# ------------------------------------------------------------------
# Import the root agent
# ------------------------------------------------------------------
from aviva_agent.agent import root_agent

# ------------------------------------------------------------------
# FastAPI application setup
# ------------------------------------------------------------------
app = FastAPI(
    title="Aviva Insurance Policy Management",
    description="AI-powered insurance policy management system",
    version="1.0.0",
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# ------------------------------------------------------------------
# ADK Session Management
# ------------------------------------------------------------------
session_service = InMemorySessionService()

# Store session mappings: browser_session_id -> adk_session_id
session_map: dict[str, str] = {}

APP_NAME = "aviva_insurance"
USER_ID_PREFIX = "user_"


async def get_or_create_session(browser_session_id: str):
    """
    Get an existing ADK session or create a new one for the browser session.

    Args:
        browser_session_id: The session ID from the browser client.

    Returns:
        The ADK session object.
    """
    if browser_session_id in session_map:
        adk_session_id = session_map[browser_session_id]
        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=f"{USER_ID_PREFIX}{browser_session_id}",
            session_id=adk_session_id,
        )
        if session:
            return session

    # Create a new session
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=f"{USER_ID_PREFIX}{browser_session_id}",
    )
    session_map[browser_session_id] = session.id
    return session


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.get("/")
async def home(request: Request):
    """Serve the main Aviva-styled landing page with chat widget."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/chat")
async def chat(request: Request):
    """
    Chat API endpoint - processes user messages through the ADK agent.

    Expects JSON: {"message": "user text", "session_id": "optional"}
    Returns JSON: {"response": "agent text", "session_id": "id"}
    """
    try:
        body = await request.json()
        user_message = body.get("message", "").strip()
        browser_session_id = body.get("session_id", str(uuid.uuid4()))

        if not user_message:
            return JSONResponse(
                status_code=400,
                content={"error": "Message cannot be empty."}
            )

        # Get or create the ADK session
        session = await get_or_create_session(browser_session_id)

        # Create a runner for the root agent
        runner = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=session_service,
        )

        # Build the user message content
        user_content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)],
        )

        # Run the agent and collect the response
        agent_response_text = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=user_content,
        ):
            # Collect text from agent responses
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        agent_response_text += part.text

        # If no response was generated, provide a fallback
        if not agent_response_text:
            agent_response_text = (
                "I apologise, but I wasn't able to process that request. "
                "Could you please rephrase or let me know how I can help?"
            )

        return JSONResponse(content={
            "response": agent_response_text,
            "session_id": browser_session_id,
        })

    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "An internal error occurred. Please try again.",
                "details": str(e),
            }
        )


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Aviva Insurance AI Assistant"}


# ------------------------------------------------------------------
# Run the server
# ------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  Aviva Insurance Policy Management System")
    print("  Starting server on http://localhost:8000")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
