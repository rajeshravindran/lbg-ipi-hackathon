from dotenv import load_dotenv
from google.adk.agents import SequentialAgent, ParallelAgent
A
from .agents.agent_1 import agent_1
from .agents.address_validator import address_validator_dq
from .agents.Image_DQ_Agent import id_extractor_agent
from .agents.documents_pensions_agent import documents_pensions_agent
from .agents.data_contract_agent import data_contract_agent
from .agents.parse_document_agent import parse_document_agent

load_dotenv(override=True)

# ✅ NO CALLBACKS
# ✅ NO inject_id_image
# ✅ NO callback_context

root_agent = SequentialAgent(
    name="LBG_IPI_DQ_CHECKS",
    description="Multimodal ID extraction and address validation pipeline",
    instructiion="""
    you are a multimodal extractor. 
    you will call all the models one by one irrespective of the outcome.
    """,
    sub_agents=[
        id_extractor_agent, 
        address_validator_dq, 
        parse_document_agent, 
        data_contract_agent, 
        documents_pensions_agent
        ]
)