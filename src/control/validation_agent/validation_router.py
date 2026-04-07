"""Module defining the router function for the validation agent graph. This module contains the logic to route the flow of the graph based on the presence or absence of purchase orders in the agent state. The router function checks the 'pos' field in the agent state and directs the flow accordingly. If there are no purchase orders present (length of 'pos' is zero), it routes to the 'skip_po' node, which handles scenarios where validation is performed without purchase orders. If there are purchase orders present, it routes to the 'match_po' node, which performs validation by matching invoices against the available purchase orders. This routing mechanism ensures that the validation process is appropriately tailored based on the input data, optimizing the workflow for different validation scenarios."""

from src.control.validation_agent.validation_state import AgentState


def router(state: AgentState) -> str:
    """Router function to determine the next step in the validation graph based on the presence or absence of purchase orders in the agent state. This function checks the 'pos' field in the agent state and routes the flow accordingly. If there are no purchase orders present (length of 'pos' is zero), it routes to the 'skip_po' node, which handles scenarios where validation is performed without purchase orders. If there are purchase orders present, it routes to the 'match_po' node, which performs validation by matching invoices against the available purchase orders. This routing mechanism ensures that the validation process is appropriately tailored based on the input data, optimizing the workflow for different validation scenarios."""
    if len(state["pos"]) == 0:
        return "skip_po"
    else:
        return "match_po"
