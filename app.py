import streamlit as st
from src.expense_audit import build_graph  
from langgraph.types import Command
import uuid

st.set_page_config(page_title="Expense Compliance Auditor", page_icon="🧾")
st.title("Expense Compliance Auditor")

DEFAULT_INVOICE = (
    "Company: Luxury Restaurant, Date: 2026.07.03 (Friday) 23:45, "
    "Amount: 120000 HUF, Item: 2 x Ribeye steak, 1 bottle of premium wine"
)

# Initialize the compiled LangGraph execution engine in the session state
if "graph" not in st.session_state:
    st.session_state.graph = build_graph()

# Set up a consistent thread ID configuration required by LangGraph's checkpointer
if "config" not in st.session_state:
    st.session_state.config = {"configurable": {"thread_id": str(uuid.uuid4())}}

# Tracking variables for UI management
if "current_state" not in st.session_state:
    st.session_state.current_state = None
if "next_node" not in st.session_state:
    st.session_state.next_node = None

invoice_text = st.text_area("Invoice OCR text", value=DEFAULT_INVOICE, height=140)

if st.button("Run audit"):
    # Kickstart the graph execution from scratch
    inputs = {"invoice_text": invoice_text}
    st.session_state.graph.invoke(inputs, st.session_state.config)
    
    # Retrieve the state snapshot directly from the graph engine
    snapshot = st.session_state.graph.get_state(st.session_state.config)
    st.session_state.current_state = snapshot.values
    st.session_state.next_node = snapshot.next


if st.session_state.current_state:
    state = st.session_state.current_state
    
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


    # Check if 'human_review' is the next node waiting in line (indicating an active interrupt)
    if st.session_state.next_node and "human_review" in st.session_state.next_node and state.get("status") == "pending_review":
        st.warning("Human review is required before the invoice can be finalized.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Approve invoice", use_container_width=True):
                decision_payload = {"approved": True, "reason": "Approved by auditor"}
                
                st.session_state.graph.invoke(
                    Command(resume=decision_payload), 
                    st.session_state.config
                )
                
                # Fetch updated state and refresh UI
                final_snapshot = st.session_state.graph.get_state(st.session_state.config)
                st.session_state.current_state = final_snapshot.values
                st.session_state.next_node = final_snapshot.next
                st.rerun()
                
        with col2:
            if st.button("Reject invoice", use_container_width=True):
                decision_payload = {"approved": False, "reason": "Alcohol is not reimbursable under policy"}
                
                st.session_state.graph.invoke(
                    Command(resume=decision_payload), 
                    st.session_state.config
                )
                
                # Fetch updated state and refresh UI
                final_snapshot = st.session_state.graph.get_state(st.session_state.config)
                st.session_state.current_state = final_snapshot.values
                st.session_state.next_node = final_snapshot.next
                st.rerun()


    # Once the state moves past the interrupt to the final steps, display the final message cleanly
    elif state.get("final_message"):
        st.markdown("---")
        if state.get("status") == "approved":
            st.success(state["final_message"])
        else:
            st.error(state["final_message"])
            
        # Optional button to clear session variables and begin auditing another input smoothly
        if st.button("Audit New Invoice"):
            st.session_state.current_state = None
            st.session_state.next_node = None
            st.session_state.config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            st.rerun()