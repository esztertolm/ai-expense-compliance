from __future__ import annotations

import os
from typing import Any, TypedDict

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langgraph.graph import END, StateGraph
from langgraph.types import interrupt
from langgraph.checkpoint.memory import MemorySaver

from langchain_groq import ChatGroq
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

load_dotenv()

class InvoiceAuditState(TypedDict, total=False):
    invoice_text: str
    extracted_data: dict[str, Any]
    red_flags: list[str]
    audit_decision: dict[str, Any]
    needs_human_review: bool
    status: str
    final_message: str

class ExtractedInvoice(BaseModel):
    """Extracted invoice data and automated compliance check flags."""
    vendor: str = Field(description="Name of the company or restaurant issuing the invoice.")
    date: str = Field(description="Date of the invoice in YYYY-MM-DD format.")
    amount: int = Field(description="The absolute final gross total amount (grand total) that the employee actually paid.")
    category: str = Field(description="Expense category (e.g., meals, travel, software, accommodation).")
    has_alcohol: bool = Field(description="True if alcohol (wine, beer, cocktails, spirits, etc.) is listed on the invoice.")
    is_weekend_or_late: bool = Field(description="True if the date falls on a weekend, or the transaction occurred late at night (after 22:00).")


def analyze_invoice(state: InvoiceAuditState) -> InvoiceAuditState:
    """
    Extracts structured invoice data using LLM and flags corporate compliance violations.
    
    Raises:
        ValueError: If the GROQ_API_KEY environment variable is not set.
    """
    invoice_text = state["invoice_text"]

    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("Missing GROQ_API_KEY! Please add it to your .env file or set it in your environment variables.")
        

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    parser = PydanticOutputParser(pydantic_object=ExtractedInvoice)

    prompt_template = PromptTemplate(
        template=(
            "Analyze the following invoice text, extract data, and check compliance rules.\n\n"
            "Identify all prices, but ensure the 'amount' field captures the final grand total paid.\n\n"
            "{format_instructions}\n\n"
            "Invoice Text:\n{invoice_text}"
        ),
        input_variables=["invoice_text"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt_template | llm | parser
    result = chain.invoke({"invoice_text": invoice_text})


    red_flags = []
    if result.has_alcohol:
        red_flags.append("Compliance Policy Violation: Alcohol detected on invoice.")
    if result.is_weekend_or_late:
        red_flags.append("Audit Warning: Expense incurred during weekend or late night.")
    if result.amount >= 50000:
        red_flags.append("Approval Limit Exceeded: Amount is 50,000 or higher.")

    return {
        **state,
        "extracted_data": result.model_dump(),
        "red_flags": red_flags,
        "status": "pending_review" if red_flags else "approved",
    }


def route_after_analysis(state: InvoiceAuditState) -> str:
    if state["red_flags"]:
        return "human_review"
    return "finalize_audit"


def human_review(state: InvoiceAuditState) -> InvoiceAuditState:
    """Human-in-the-Loop node. Execution pauses here until UI provides input."""
    # If the decision is already in the state (resumed from UI)
    if state.get("audit_decision"):
        return state

    # If no decision, LangGraph forces a pause here
    review_payload = {
        "invoice": state["extracted_data"],
        "red_flags": state["red_flags"],
    }
    
    # The interrupt pauses execution and yields this payload to the UI
    decision = interrupt(review_payload)
    
    return {
        **state,
        "audit_decision": decision,
        "status": "approved" if decision.get("approved") else "rejected"
    }


def finalize_audit(state: InvoiceAuditState) -> InvoiceAuditState:
    """Closes the process and generates the final status message."""
    vendor = state["extracted_data"].get("vendor", "Unknown")
    
    # Automatically approved if no red flags triggered the human review
    if not state.get("audit_decision"):
        return {
            **state,
            "status": "approved",
            "final_message": f"Invoice from {vendor} automatically APPROVED by System Compliance."
        }
        
    # If it went through human review
    decision = state["audit_decision"]
    if decision.get("approved"):
        return {
            **state,
            "final_message": f"Invoice from {vendor} APPROVED by Manager. Note: {decision.get('reason', 'None')}"
        }
    else:
        return {
            **state,
            "final_message": f"Invoice from {vendor} REJECTED by Manager. Reason: {decision.get('reason', 'Policy violation')}"
        }


def build_graph() -> StateGraph:
    graph = StateGraph(InvoiceAuditState)
    graph.add_node("analyze_invoice", analyze_invoice)
    graph.add_node("human_review", human_review)
    graph.add_node("finalize_audit", finalize_audit)
    graph.set_entry_point("analyze_invoice")
    graph.add_conditional_edges(
        "analyze_invoice",
        route_after_analysis,
        {
            "human_review": "human_review",
            "finalize_audit": "finalize_audit",
        },
    )
    graph.add_edge("human_review", "finalize_audit")
    graph.add_edge("finalize_audit", END)
    memory = MemorySaver()
    return graph.compile(checkpointer = memory, name="expense_audit_graph")
