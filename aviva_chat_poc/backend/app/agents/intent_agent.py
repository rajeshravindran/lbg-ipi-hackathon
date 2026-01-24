from agents.base import BaseAgent
from llm.llm_client import LlmClient
import json

class IntentAgent(BaseAgent):
    name = "intent_agent"

    def __init__(self):
        self.llm = LlmClient()

    async def run(self, context: dict) -> dict:
        prompt = f"""
        Extract motor insurance intent and fields from the message.
        Return ONLY valid JSON with these fields:
        {{"intent": "", "vehicle_reg": "", "driver_age": "", "postcode": ""}}

        Message: {context["user_message"]}
        
        Response must be valid JSON only, no markdown, no explanation.
        """
        result = await self.llm.complete(
            system_prompt="You are a Motor insurance agent. Always respond with valid JSON only.",
            user_prompt=prompt
        )

        print(f"LLM Response: '{result}'")
        result = result.strip()
        if result.startswith("```json"):
            result = result.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {e}")
            print(f"Raw result: {result}")
            # Return a default structure instead of crashing
            return {
                "intent": "quote_request",
                "vehicle_reg": "",
                "driver_age": "",
                "postcode": "",
                "error": f"Failed to parse LLM response: {str(e)}"
            }