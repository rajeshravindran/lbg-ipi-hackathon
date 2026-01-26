from agents.base import BaseAgent
from llm.llm_client import LlmClient
import json

class ClaimsAgent(BaseAgent):
    name = "claims_agent"

    def __init__(self) -> None:
        self.llm = LlmClient()

    async def run(self, context: dict) -> dict:
        result = await self.llm.complete(
            system_prompt="You are a claims history system.",
            user_prompt="Return claims_count as JSON."
        )
        return json.loads(result)
