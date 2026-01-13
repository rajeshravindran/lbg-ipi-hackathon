from dotenv import load_dotenv
from google.adk.agents import SequentialAgent, ParallelAgent

from .agents.agent_1 import agent_1
from .agents.agent_2 import agent_2
from .agents.Image_DQ_Agent import id_extractor_agent

load_dotenv(override=True)

# ✅ NO CALLBACKS
# ✅ NO inject_id_image
# ✅ NO callback_context

address_DQ_agent = SequentialAgent(
    name="Address_Validator_Agent",
    description="Multimodal ID extraction and address validation pipeline",
    sub_agents=[agent_1, agent_2]
)

card_address_DQ_agent = SequentialAgent(
    name="Card_Address_Validator_Agent", 
    description="extracts the address information from card and passes to Agent2"
    sub_agents=[id_extractor_agent, agent_2]
)

root_agent = ParallelAgent(
    name='LBG_Integration_Orchestrator',
    description="Parallel execution of ID processing and supplementary checks",
    sub_agents=[card_address_DQ_agent, address_DQ_agent]
)