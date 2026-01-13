from dotenv import load_dotenv
from google.adk.agents import SequentialAgent

from .agents.agent_1 import agent_1
from .agents.agent_2 import agent_2

load_dotenv(override=True)

# ✅ NO CALLBACKS
# ✅ NO inject_id_image
# ✅ NO callback_context

root_agent = SequentialAgent(
    name="LBG_Integration_Orchestrator",
    description="Multimodal ID extraction and address validation pipeline",
    sub_agents=[agent_1, agent_2]
)