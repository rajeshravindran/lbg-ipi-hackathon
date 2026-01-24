from agents.base import BaseAgent
from llm.llm_client import LlmClient
import json

class CreditAgent(BaseAgent):
    name = "credit_agent"

    def __init__(self) -> None:
        self.llm = LlmClient()

    async def run(self, context: dict) -> dict:
        result = await self.llm.complete(
            system_prompt="You are a Credit history system.",
            user_prompt="Return Credit Score as JSON."
        )
        return json.loads(result)
