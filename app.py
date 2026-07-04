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

invoice_text = st.text_area("Invoice OCR text", value=DEFAULT_INVOICE, height=140)

if st.button("Run audit"):
    state = analyze_invoice({"invoice_text": invoice_text})
    st.session_state.audit_state = state

state = st.session_state.audit_state or {}

if state:
    st.subheader("Audit status")
    st.write(f"Status: {state.get('status', 'pending')}")

    st.subheader("Extracted invoice data")
    st.json(state.get("extracted_data", {}))

    st.subheader("Red flags")
    red_flags = state.get("red_flags", [])
    if red_flags:
        for flag in red_flags:
            st.warning(flag)
    else:
        st.success("No compliance issues detected.")

    if state.get("red_flags"):
        st.warning("Human review is required before the invoice can be finalized.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Approve invoice"):
                state["audit_decision"] = {"approved": True, "reason": "Approved by auditor"}
                state = finalize_audit(state)
                st.session_state.audit_state = state
                st.success(state.get("final_message", ""))
        with col2:
            if st.button("Reject invoice"):
                state["audit_decision"] = {"approved": False, "reason": "Alcohol is not reimbursable under policy"}
                state = finalize_audit(state)
                st.session_state.audit_state = state
                st.error(state.get("final_message", ""))
    elif state.get("final_message"):
        st.success(state["final_message"])
