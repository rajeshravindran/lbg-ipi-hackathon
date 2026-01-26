from agents.base import BaseAgent
from llm.llm_client import LlmClient
import json

class UnderwritingAgent(BaseAgent):
    name = "underwriting_agent"

    def __init__(self):
        self.llm = LlmClient()

    async def run(self, context: dict) -> dict:
        prompt = f"""
        Assess insurance risk.
        Inputs:
        {context}
        
        Return JSON with risk_score (0-1).
        """

        result = await self.llm.complete(
            system_prompt="You are an insurance underwriter.",
            user_prompt=prompt
        )

        return json.loads(result)

