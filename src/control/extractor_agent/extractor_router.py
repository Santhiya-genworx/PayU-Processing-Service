"""Module defining the router function for the extractor agent graph. This module contains the logic to route the flow of the graph based on the file type of the input document. The router function checks the 'file_type' field in the agent state and directs the flow to the appropriate node in the graph for processing. If the file type is 'image', it routes to the 'vision_extractor' node, and if it is 'pdf', it routes to the 'type_detector' node. If the file type does not match either of these, it routes to the 'end' node, effectively terminating the graph execution. This routing mechanism ensures that different types of inputs are handled by the correct extraction agents, optimizing the processing workflow for various document formats."""

from src.control.extractor_agent.extractor_state import AgentState
from src.observability.logging.logging_config import logger


def router(state: AgentState) -> str:
    """Router function to determine the next step in the extractor graph based on the file type of the input document. This function checks the 'file_type' field in the agent state and routes the flow accordingly. If the file type is 'image', it directs to the 'vision_extractor' node for processing. If the file type is 'pdf', it routes to the 'type_detector' node for further analysis. If the file type does not match either of these, it routes to the 'end' node, effectively terminating the graph execution. This routing logic ensures that different types of inputs are handled by the appropriate extraction agents, optimizing the processing workflow for various document formats."""
    logger.info("Router...")
    if state["file_type"] == "image":
        return "image"
    elif state["file_type"] == "pdf":
        return "text"
    else:
        return "end"
