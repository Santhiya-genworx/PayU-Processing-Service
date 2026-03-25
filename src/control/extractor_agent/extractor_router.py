from src.control.extractor_agent.extractor_state import AgentState
from src.observability.logging.logging_config import logger


def router(state: AgentState) -> str:
    logger.info("Router...")
    if state["file_type"] == "image":
        return "image"
    elif state["file_type"] == "pdf":
        return "text"
    else:
        return "end"
