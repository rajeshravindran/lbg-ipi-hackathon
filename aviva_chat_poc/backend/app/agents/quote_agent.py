from agents.base import BaseAgent
from llm.llm_client import LlmClient
import json

class QuoteAgent(BaseAgent):
    name = "quote_agent"

    def __init__(self):
        self.llm = LlmClient()

    async def run(self, context: dict) -> dict:
        prompt = f"""
        Present quotes conversationally.
        Data:
        {context}
        """

        message = await self.llm.complete(
            system_prompt="You are a customer-facing insurance chatbot.",
            user_prompt=prompt
        )

        return {"message": message}

