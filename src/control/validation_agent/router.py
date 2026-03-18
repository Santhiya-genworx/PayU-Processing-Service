from src.control.validation_agent.state import AgentState

def router(state: AgentState):
    if state["po"] is None:
        return "skip_po"
    else:
        return "match_po"