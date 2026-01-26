from agents.base import BaseAgent
from llm.llm_client import LlmClient
import json

class DVLAAgent(BaseAgent):
    name = "dvla_agent"

    def __init__(self) -> None:
        self.llm = LlmClient()

    async def run(self, context: dict) -> dict:
        prompt = f"""
        Given vehicle reg {context['vehicle_reg']},
        return realistic UK vehicle details as JSON.
        """

        result = await self.llm.complete(
            system_prompt="You are a DVLA vehicle database.",
            user_prompt=prompt
        )

        return json.loads(result)