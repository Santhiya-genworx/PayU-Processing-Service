from src.control.validation_agent.validation_state import AgentState


def router(state: AgentState) -> str:
    if len(state["pos"]) == 0:
        return "skip_po"
    else:
        return "match_po"
