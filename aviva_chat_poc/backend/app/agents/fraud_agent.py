from agents.base import BaseAgent
from llm.llm_client import LlmClient
import json

class FraudAgent(BaseAgent):
    name = "fraud_agent"

    def __init__(self) -> None:
        self.llm = LlmClient()

    async def run(self, context: dict) -> dict:
        result = await self.llm.complete(
            system_prompt="You are a insurance/credit fraud monitoring system.",
            user_prompt="Return fraud risk as JSON."
        )
        return json.loads(result)
