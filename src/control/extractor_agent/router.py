from src.control.extractor_agent.state import AgentState

def router(state: AgentState):
    print("Router...")
    if state["file_type"] == "image":
        return "image"
    elif state["file_type"] == "pdf":
        return "text"
    else:
        return "end"