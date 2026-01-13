from google.adk.agents import LlmAgent

data_contract_agent=LlmAgent(
    name='data_contract_agent',
    description="data_contract_agent",
    instruction="""
    you will respond back with message hello from data_contract_agent
    """
)