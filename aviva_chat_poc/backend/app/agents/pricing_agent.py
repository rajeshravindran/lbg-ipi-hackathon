from agents.base import BaseAgent
from llm.llm_client import LlmClient
import json

class PricingAgent(BaseAgent):
    name = "pricing_agent"

    def __init__(self) -> None:
        self.llm = LlmClient()

    async def run(self, context: dict) -> dict:

        prompt = f"""
        Generate standard and premium quotes based on risk_score.
        Return JSON with standard_quote, premium_quote.
        """
        result = await self.llm.complete(
            system_prompt="You are a Pricing engine.",
            user_prompt=prompt
        )

        return json.loads(result)

