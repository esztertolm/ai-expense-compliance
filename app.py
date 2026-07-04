import streamlit as st
from src.expense_audit import build_graph  
from langgraph.types import Command
import uuid
from src.db import init_db, get_audit_history
import yaml

init_db()

# Load the dynamic configuration data from the external file
with open("config.yaml", "r", encoding="utf-8") as file:
    config_data = yaml.safe_load(file)

# Extract structured definitions from the loaded dictionary
MOCK_SAMPLES = config_data.get("samples", {})
DEFAULT_INVOICE = config_data.get("default_invoice", "")

st.set_page_config(layout="wide")
tab_audit, tab_history = st.tabs(["🧾 Live Audit", "🗄️ Audit History Logs"])

with tab_audit:
    st.set_page_config(page_title="Expense Compliance Auditor", page_icon="🧾")
    st.title("Expense Compliance Auditor")

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

    # Quick sample data selectbox generated dynamically from the YAML file keys
    sample_option = st.selectbox(
        "Choose a sample invoice scenario to test:",
        options=list(MOCK_SAMPLES.keys())
    )

    # Automatically fetch text mappings without complex nested conditional blocks
    invoice_text_value = MOCK_SAMPLES.get(sample_option, DEFAULT_INVOICE)
    invoice_text = st.text_area("Invoice OCR text", value=invoice_text_value, height=140)

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
        extracted_data = state.get("extracted_data", {})
        if extracted_data:
            # Format the dictionary into a clean two-column table for better UI
            table_data = {
                "Field": [key.replace("_", " ").title() for key in extracted_data.keys()],
                "Value": [str(value) for value in extracted_data.values()]
            }
            st.table(table_data)

        st.subheader("Red flags")
        red_flags = state.get("red_flags", [])
        if red_flags:
            for flag in red_flags:
                st.error(flag)
        else:
            st.success("No compliance issues detected.")


        # Check if 'human_review' is the next node waiting in line (indicating an active interrupt)
        if st.session_state.next_node and "human_review" in st.session_state.next_node and state.get("status") == "pending_review":
            st.warning("Human review is required before the invoice can be finalized.")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Approve invoice"):
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
                if st.button("Reject invoice"):
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

with tab_history:
    st.markdown("#### 🗄️ Historical Audit Logs")
    st.markdown("A persistent record of all automated and human-reviewed invoice decisions.")
    
    # Add a refresh button
    if st.button("🔄 Refresh History"):
        st.rerun()
        
    # Load and display the database
    df_history = get_audit_history()
    
    if df_history.empty:
        st.info("No audit logs found yet. Run an audit to generate history.")
    else:
        # Streamlit's native dataframe viewer allows sorting and scrolling
        st.dataframe(
            df_history, 
            hide_index=True
        )