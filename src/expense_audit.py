from __future__ import annotations

import os
from dotenv import load_dotenv

from langgraph.graph import END, StateGraph
from langgraph.types import interrupt
from langgraph.checkpoint.memory import MemorySaver

from langchain_groq import ChatGroq
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage

from src.db import save_audit_log
from src.schemas import InvoiceAuditState, ExtractedInvoice
from src.rules import check_compliance_rules

load_dotenv()

def analyze_invoice(state: InvoiceAuditState) -> InvoiceAuditState:
    invoice_text = state["invoice_text"]
    invoice_image = state.get("invoice_image")

    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("Missing GROQ_API_KEY!")
        
    parser = PydanticOutputParser(pydantic_object=ExtractedInvoice)
    format_instructions = parser.get_format_instructions()


    if invoice_image:
        llm = ChatGroq(model="qwen/qwen3.6-27b", temperature=0)

        vision_instruction = (
            "Analyze the invoice data, extract fields, and check compliance rules based on the attached photo.\n\n"
            "Identify all prices, but ensure the 'amount' field captures the final grand total paid.\n\n"
            "CRITICAL: You must return ONLY a raw JSON code block matching the schema below.\n"
            "Do NOT include any conversational text, explanations, markdown headers, or introductory notes.\n"
            "Just the valid JSON object itself.\n\n"
            f"REQUIRED JSON SCHEMA:\n{format_instructions}"
        )

        message = HumanMessage(
            content=[
                {"type": "text", "text": vision_instruction},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{invoice_image}"}},
            ]
        )
        response = llm.invoke([message])
        result = parser.parse(response.content)

    else:
        llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
        
        system_instruction = (
            "Analyze the invoice data, extract fields, and check compliance rules.\n\n"
            "Identify all prices, but ensure the 'amount' field captures the final grand total paid.\n\n"
            f"{format_instructions}"
        )
        prompt_template = PromptTemplate(
            template="{system_instruction}\n\nInvoice Text:\n{invoice_text}",
            input_variables=["invoice_text"],
            partial_variables={"system_instruction": system_instruction},
        )
        chain = prompt_template | llm | parser
        result = chain.invoke({"invoice_text": invoice_text})

    # Use the extracted rules engine
    red_flags = check_compliance_rules(result)

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
    """Closes the process, generates the final status message, and saves to DB."""
    vendor = state["extracted_data"].get("vendor", "Unknown")
    amount = state["extracted_data"].get("amount", 0)
    
    # Generate the final state data
    if not state.get("audit_decision"):
        status = "APPROVED"
        reason = "Auto-approved by System Compliance"
        final_message = f"Invoice from {vendor} automatically APPROVED by System Compliance."
    else:
        decision = state["audit_decision"]
        if decision.get("approved"):
            status = "APPROVED"
            reason = decision.get("reason", "None")
            final_message = f"Invoice from {vendor} APPROVED by Manager. Note: {reason}"
        else:
            status = "REJECTED"
            reason = decision.get("reason", "Policy violation")
            final_message = f"Invoice from {vendor} REJECTED by Manager. Reason: {reason}"
            
    save_audit_log(vendor, amount, status, reason)

    return {
        **state,
        "status": status.lower(),
        "final_message": final_message
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
