
import pandas as pd
import streamlit as st

from theme import inject_theme, page_header, render_sidebar

inject_theme()
render_sidebar("analysis")

page_header(
    "Your Water Allocation Plan",
    "A practical rainwater allocation plan for your household.",
)

result = st.session_state.get("simulation_result")

if result is None:
    st.info("Please configure your household and run a simulation.")
    if st.button("Start Planning", type="primary"):
        st.switch_page("pages/configuration.py")
    st.stop()

df = result["data"]
summary = result["summary"]
config = st.session_state.get("simulation_config") or {}

place = st.session_state.get("selected_place")
source = result.get("source")
if place or source:
    info = []
    if place:
        info.append(f"Location: {place}")
    if source:
        info.append(f"Rainfall source: {source}")
    st.caption(" | ".join(info))

days = len(df)

if days == 0:
    st.error("No simulation data available.")
    st.stop()

# ---------------------------------------
# Calculate allocation statistics
# ---------------------------------------

primary_used = float(df["primary_used_l"].sum())
secondary_used = float(df["secondary_used_l"].sum())
external_supply = float(df["external_supply_l"].sum())
secondary_shortage = float(df["secondary_shortage_l"].sum())

primary_demand = primary_used + external_supply
secondary_demand = secondary_used + secondary_shortage

primary_coverage = (
    primary_used / primary_demand * 100
    if primary_demand > 0 else 100.0
)

secondary_coverage = (
    secondary_used / secondary_demand * 100
    if secondary_demand > 0 else 100.0
)

primary_shortage_days = int(
    (df["external_supply_l"] > 0).sum()
)

secondary_shortage_days = int(
    (df["secondary_shortage_l"] > 0).sum()
)

# ---------------------------------------
# Overview
# ---------------------------------------

st.subheader("Water Supply Overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Rainwater Collected",
    f"{summary['collected']:.1f} L"
)

c2.metric(
    "Primary Demand Covered",
    f"{primary_coverage:.1f}%"
)

c3.metric(
    "Secondary Demand Covered",
    f"{secondary_coverage:.1f}%"
)

c4.metric(
    "Final Tank Storage",
    f"{summary['final_storage']:.1f} L"
)

st.divider()

# ---------------------------------------
# Recommended allocation
# ---------------------------------------

st.subheader("Recommended Water Allocation")

st.write(
    "RainWise prioritises essential household water use "
    "before allocating remaining rainwater to irrigation."
)

left, right = st.columns(2)

with left:
    st.markdown("#### Priority 1 — Toilet Flushing")

    st.metric(
        "Rainwater Allocated",
        f"{primary_used:.1f} L"
    )

    st.progress(
        min(max(primary_coverage / 100, 0.0), 1.0)
    )

    st.caption(
        f"Demand: {primary_demand:.1f} L | "
        f"Coverage: {primary_coverage:.1f}%"
    )

with right:
    st.markdown("#### Priority 2 — Garden & Lawn")

    st.metric(
        "Rainwater Allocated",
        f"{secondary_used:.1f} L"
    )

    st.progress(
        min(max(secondary_coverage / 100, 0.0), 1.0)
    )

    st.caption(
        f"Demand: {secondary_demand:.1f} L | "
        f"Coverage: {secondary_coverage:.1f}%"
    )

st.divider()

# ---------------------------------------
# Actionable recommendations
# ---------------------------------------

st.subheader("Your Water Management Recommendations")

if external_supply > 0:
    st.warning(
        f"Essential water shortage: {external_supply:.1f} L "
        f"of external supply is required over {days} days. "
        f"Primary demand was not fully met by rainwater "
        f"on {primary_shortage_days} day(s)."
    )
else:
    st.success(
        "Your rainwater supply met all primary household "
        "demand during the simulated period."
    )

if secondary_shortage > 0:
    st.warning(
        f"Irrigation shortage: {secondary_shortage:.1f} L "
        f"over {days} days. Reduce or postpone non-essential "
        f"irrigation during low-storage periods."
    )
else:
    st.success(
        "All secondary irrigation demand was met "
        "during the simulated period."
    )

if summary["overflow"] > 0:
    st.info(
        f"Overflow detected: {summary['overflow']:.1f} L "
        "of collected rainwater exceeded tank capacity. "
        "A larger tank may reduce overflow, but its "
        "benefit should be tested before recommending it."
    )

reserve = float(config.get("reserve", 0.0))

if summary["final_storage"] <= reserve:
    st.info(
        "Final storage is at or below the reserve target. "
        "Consider reducing discretionary water use "
        "before the next low-rainfall period."
    )

# ---------------------------------------
# Daily allocation schedule
# ---------------------------------------

st.divider()
st.subheader("Daily Water Allocation Schedule")

schedule = df[
    [
        "day",
        "rain_mm",
        "primary_used_l",
        "secondary_used_l",
        "external_supply_l",
        "secondary_shortage_l",
        "end_l",
    ]
].copy()

schedule.columns = [
    "Day",
    "Rainfall (mm)",
    "Toilet Allocation (L)",
    "Irrigation Allocation (L)",
    "External Supply (L)",
    "Irrigation Shortage (L)",
    "Tank Remaining (L)",
]

if "date" in df.columns:
    schedule.insert(1, "Date", df["date"])

st.dataframe(
    schedule.round(2),
    use_container_width=True,
    hide_index=True
)

st.download_button(
    "Download Water Allocation Plan (CSV)",
    data=schedule.to_csv(index=False).encode("utf-8-sig"),
    file_name="rainwise_water_allocation_plan.csv",
    mime="text/csv",
)

# ---------------------------------------
# Optional detailed charts
# ---------------------------------------

with st.expander("View Detailed Simulation Charts"):

    index_col = "date" if "date" in df.columns else "day"
    chart_df = df.set_index(index_col)

    st.markdown("#### Daily Water Allocation")

    st.bar_chart(
        chart_df[["primary_used_l", "secondary_used_l"]]
    )

    st.markdown("#### Tank Storage")

    st.line_chart(
        chart_df["end_l"]
    )

st.divider()

if st.button("Modify Household Configuration"):
    st.switch_page("pages/configuration.py")
