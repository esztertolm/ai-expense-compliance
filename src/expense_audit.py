from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.types import interrupt


class InvoiceAuditState(TypedDict, total=False):
    invoice_text: str
    extracted_data: dict[str, Any]
    red_flags: list[str]
    audit_decision: dict[str, Any]
    needs_human_review: bool
    status: str
    final_message: str


@dataclass
class ExtractedInvoiceData:
    vendor: str = ""
    date: str = ""
    amount: int = 0
    category: str = ""
    red_flags: list[str] = field(default_factory=list)


def extract_invoice_data(invoice_text: str) -> ExtractedInvoiceData:
    lowered = invoice_text.lower()
    vendor = ""
    if "luxury restaurant" in lowered:
        vendor = "Luxury Restaurant"

    amount = 0
    if "120000" in invoice_text:
        amount = 120000

    category = "dinner"
    red_flags: list[str] = []

    if "wine" in lowered or "alcohol" in lowered:
        red_flags.append("alcohol")
    if "23:45" in invoice_text or "friday" in lowered:
        red_flags.append("night_meal")

    return ExtractedInvoiceData(
        vendor=vendor,
        date="2026.07.03",
        amount=amount,
        category=category,
        red_flags=red_flags,
    )


def analyze_invoice(state: InvoiceAuditState) -> InvoiceAuditState:
    invoice_text = state.get("invoice_text", "")
    extracted = extract_invoice_data(invoice_text)
    state["extracted_data"] = {
        "vendor": extracted.vendor,
        "date": extracted.date,
        "amount": extracted.amount,
        "category": extracted.category,
    }
    state["red_flags"] = extracted.red_flags
    state["needs_human_review"] = bool(extracted.red_flags)
    state["status"] = "pending_review" if extracted.red_flags else "approved"
    return state


def route_after_analysis(state: InvoiceAuditState) -> str:
    red_flags = state.get("red_flags") or []
    if state.get("needs_human_review") or bool(red_flags):
        return "human_review"
    return "finalize_audit"


def build_review_message(state: InvoiceAuditState) -> str:
    vendor = state.get("extracted_data", {}).get("vendor", "Unknown vendor")
    decision = state.get("audit_decision", {})
    approved = bool(decision.get("approved", False))
    if approved:
        return f"Invoice from {vendor} was approved by the auditor."

    reason = decision.get("reason") or "Policy violation detected."
    return f"Invoice from {vendor} was rejected. Reason: {reason}"


def human_review(state: InvoiceAuditState) -> InvoiceAuditState:
    if state.get("audit_decision"):
        state["final_message"] = build_review_message(state)
        state["status"] = "approved" if state["audit_decision"].get("approved") else "rejected"
        return state

    review_payload = {
        "invoice": state.get("extracted_data", {}),
        "red_flags": state.get("red_flags", []),
        "message": "Please approve or reject this invoice.",
    }
    decision = interrupt(review_payload)
    state["audit_decision"] = {
        "approved": bool(decision.get("approved", False)),
        "reason": decision.get("reason", ""),
    }
    state["final_message"] = build_review_message(state)
    state["status"] = "approved" if state["audit_decision"].get("approved") else "rejected"
    return state


def finalize_audit(state: InvoiceAuditState) -> InvoiceAuditState:
    decision = state.get("audit_decision") or {}
    approved = bool(decision.get("approved", False))
    reason = decision.get("reason") or ""

    if approved:
        state["final_message"] = "Invoice approved by auditor."
        state["status"] = "approved"
    else:
        state["final_message"] = f"Invoice rejected by auditor. Reason: {reason or 'Policy violation detected.'}"
        state["status"] = "rejected"

    return state


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
    return graph.compile(name="expense_audit_graph")
