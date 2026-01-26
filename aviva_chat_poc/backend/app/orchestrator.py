import asyncio
from agents.intent_agent import IntentAgent
from agents.dvla_agent import DVLAAgent
from agents.claims_agent import ClaimsAgent
from agents.credit_agent import CreditAgent
from agents.fraud_agent import FraudAgent
from agents.underwriting_agent import UnderwritingAgent
from agents.pricing_agent import PricingAgent
from agents.quote_agent import QuoteAgent

class ChatOrchestrator:

    async def run(self, user_message: str) -> dict:
        
        try:
            context = {"user_message": user_message}
            

            # 1️⃣ Intent
            context.update(await IntentAgent().run(context))

            # 2️⃣ Parallel enrichment
            enrichment = await asyncio.gather(
                DVLAAgent().run(context),
                ClaimsAgent().run(context),
                CreditAgent().run(context),
                FraudAgent().run(context),
            )

            for data in enrichment:
                context.update(data)

            # 3️⃣ Risk & pricing
            context.update(await UnderwritingAgent().run(context))
            context.update(await PricingAgent().run(context))

            # 4️⃣ Final response
            return await QuoteAgent().run(context)
        except Exception as e:
            return {"bot_response": f"Error: {str(e)}"}
