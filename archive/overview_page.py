
import streamlit as st

st.title("Rainwater Overview")
st.caption("Household rainwater management dashboard")

result = st.session_state.get("simulation_result")

if result is None:

    st.info(
        "No simulation results yet. "
        "Configure your household to get started."
    )

    if st.button("Start Configuration", type="primary"):
        st.switch_page("pages/configuration.py")

else:

    summary = result["summary"]
    df = result["data"]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Collected Water",
        f"{summary['collected']:.1f} L"
    )

    c2.metric(
        "Final Storage",
        f"{summary['final_storage']:.1f} L"
    )

    c3.metric(
        "External Supply",
        f"{summary['external']:.1f} L"
    )

    c4.metric(
        "Water Shortage",
        f"{summary['shortage']:.1f} L"
    )

    st.divider()

    st.subheader("Daily Tank Storage")

    index_col = "date" if "date" in df.columns else "day"

    st.line_chart(
        df.set_index(index_col)["end_l"]
    )

    st.subheader("Simulation Information")

    st.write("Rainfall Source:", result["source"])

    if st.button("Detailed Analysis"):
        st.switch_page("pages/analysis.py")
