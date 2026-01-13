from google.adk.agents import LlmAgent

parse_document_agent=LlmAgent(
    name='parse_document_agent',
    description="parse_document_agent",
    instruction="""
    you will respond back with message hello from parse document agent
    """
)