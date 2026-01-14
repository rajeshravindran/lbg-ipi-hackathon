from dotenv import load_dotenv
from google.adk.agents import SequentialAgent, ParallelAgent
from google.adk.agents import LlmAgent
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
        #id_extractor_agent, 
        #address_validator_dq, 
        #parse_document_agent, 
        #data_contract_agent, 
        document_pensions_agent
        ]
)

"""
root_agent = LlmAgent(
    name="LBG_IPI_DQ_CHECKS",
    model="gemini-2.5-flash",
    description="Main entry point that routes queries to specialized sub-agents.",
    instruction=
    You are the central routing agent for LBG IPI Data Quality checks.
    Your job is to analyze the user's request and call the appropriate specialized agent:
    
    1. If the user provides an image or asks to extract ID details, use 'id_extractor_agent'.
    2. If the user asks about dormant accounts, pension records, or LinkedIn verification, use 'DormantPensionsAccount'.
    3. If the user asks to validate an address, use 'address_validator_dq'.
    
    Only call the agent that is directly relevant to the user's question.
    ,
    # Provide agents as tools so the LLM can decide which one to trigger
    tools=[
        id_extractor_agent, 
        document_pensions_agent
        # address_validator_dq, 
        # parse_document_agent, 
        # data_contract_agent,
    ]
)

root_agent = ParallelAgent(
    name="LBG_IPI_DQ_CHECKS",
    description="Multimodal ID extraction and address validation pipeline",
    sub_agents=[
        id_extractor_agent, 
        #address_validator_dq, 
        #parse_document_agent, 
        #data_contract_agent, 
        document_pensions_agent
        ]
)
"""