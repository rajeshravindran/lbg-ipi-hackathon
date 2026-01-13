from google.adk.agents import LlmAgent

document_pension_agent=LlmAgent(
    name='document_pension_agent',
    description="document_pension_agent",
    instruction="""
    you will respond back with message hello from document_pension_agent
    """
)