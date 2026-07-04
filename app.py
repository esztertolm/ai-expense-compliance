import streamlit as st

from src.expense_audit import analyze_invoice, finalize_audit


st.set_page_config(page_title="Expense Compliance Auditor", page_icon="🧾")
st.title("Expense Compliance Auditor")

DEFAULT_INVOICE = (
    "Company: Luxury Restaurant, Date: 2026.07.03 (Friday) 23:45, "
    "Amount: 120000 HUF, Item: 2 x Ribeye steak, 1 bottle of premium wine"
)

if "audit_state" not in st.session_state:
    st.session_state.audit_state = {}

invoice_text = st.text_area("Invoice OCR text", value=DEFAULT_INVOICE, height=120)

if st.button("Run audit"):
    state = analyze_invoice({"invoice_text": invoice_text})
    st.session_state.audit_state = state

state = st.session_state.audit_state
if state:
    st.subheader("Extracted invoice data")
    st.json(state.get("extracted_data", {}))

    st.subheader("Red flags")
    if state.get("red_flags"):
        st.write(state["red_flags"])
    else:
        st.write("No compliance issues detected.")

    if state.get("needs_human_review"):
        st.warning("Human review is required before the invoice can be finalized.")

        if st.button("Approve invoice"):
            state["audit_decision"] = {"approved": True, "reason": "Approved by auditor"}
            state = finalize_audit(state)
            st.session_state.audit_state = state
            st.success(state.get("final_message", ""))

        if st.button("Reject invoice"):
            state["audit_decision"] = {"approved": False, "reason": "Alcohol is not reimbursable under policy"}
            state = finalize_audit(state)
            st.session_state.audit_state = state
            st.error(state.get("final_message", ""))
    elif state.get("final_message"):
        st.success(state["final_message"])
