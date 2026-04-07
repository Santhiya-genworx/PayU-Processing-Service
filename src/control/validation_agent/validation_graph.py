"""Module defining the validation graph for processing and validating invoices against purchase orders. This module utilizes a state graph to orchestrate the flow of data through various agent functions responsible for matching vendors, line items, prices, and quantities. The graph is designed to handle different scenarios based on the presence or absence of purchase orders, routing the flow accordingly to ensure accurate validation. The main function, invoke_graph, serves as the entry point for invoking the graph with the necessary invoice and purchase order data, returning the validation results in a structured format. The module also includes error handling to manage exceptions that may arise during the validation process, ensuring that meaningful error messages are provided when issues occur."""

from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from src.control.validation_agent.agents.validation_agents import (
    decision_agent,
    line_item_match_agent,
    price_check_node,
    quantity_price_match_agent,
    vendor_match_node,
)
from src.control.validation_agent.validation_router import router
from src.control.validation_agent.validation_state import AgentState
from src.schemas.graph_output_schema import GraphResult
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest

workflow = StateGraph(AgentState)

workflow.add_node("vendor_match", vendor_match_node)
workflow.add_node("line_item_match", line_item_match_agent)
workflow.add_node("price_check", price_check_node)
workflow.add_node("quantity_price_match", quantity_price_match_agent)
workflow.add_node("decision_agent", decision_agent)

workflow.add_conditional_edges(
    START, router, {"skip_po": "price_check", "match_po": "vendor_match"}
)
workflow.add_edge("vendor_match", "line_item_match")
workflow.add_edge("line_item_match", "price_check")

workflow.add_conditional_edges(
    "price_check",
    router,
    {"skip_po": "decision_agent", "match_po": "quantity_price_match"},
)

workflow.add_edge("quantity_price_match", "decision_agent")
workflow.add_edge("decision_agent", END)

graph = workflow.compile()


async def invoke_graph(
    invoice_data: list[InvoiceRequest],
    po_data: list[PurchaseOrderRequest],
) -> GraphResult:
    """Function to invoke the validation graph with the provided invoice and purchase order data. This function initializes the agent state based on the input parameters and then invokes the compiled graph to perform the validation process. The result from the graph is processed to return the validation results in a structured format defined by the GraphResult schema. If any errors occur during the graph invocation, they are caught and raised as exceptions with details about the error. Args:   invoice_data (list[InvoiceRequest]): A list of invoice data to be validated against purchase orders. po_data (list[PurchaseOrderRequest]): A list of purchase order data to be used for validation against invoices. Returns:    A GraphResult object containing the results of the validation process, including any matches or discrepancies found between the invoices and purchase orders."""
    try:
        state: AgentState = {
            "invoices": invoice_data,
            "pos": po_data,
        }

        result = await graph.ainvoke(cast(Any, state))

        return cast(GraphResult, result)

    except Exception:
        raise
