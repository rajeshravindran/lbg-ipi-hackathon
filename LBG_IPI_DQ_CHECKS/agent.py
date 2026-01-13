from dotenv import load_dotenv
from google.adk.agents import SequentialAgent, ParallelAgent
from .agents.agent_1 import agent_1
from .agents.address_validator import address_validator_dq
from .agents.Image_DQ_Agent import id_extractor_agent
from .agents.document_pensions_agent import document_pensions_agent
from .agents.data_contract_agent import data_contract_agent
from .agents.parse_document_agent import parse_document_agent

load_dotenv(override=True)

# ✅ NO CALLBACKS
# ✅ NO inject_id_image
# ✅ NO callback_context

root_agent = SequentialAgent(
    name="LBG_IPI_DQ_CHECKS",
    description="Multimodal ID extraction and address validation pipeline",
    sub_agents=[
        id_extractor_agent, 
        address_validator_dq, 
        parse_document_agent, 
        data_contract_agent, 
        document_pensions_agent
        ]
)