
# app.py
"""RainWise - Location-based household rainwater planner."""

from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from calculator import simulate_period
from input_data import load_rainfall_csv
from water_demand import calculate_total_demand
from weather_api import get_historical_rainfall


BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="RainWise",
    page_icon="💧",
    layout="wide",
)

st.title("💧 RainWise")
st.subheader("Location-Based Household Rainwater Planning System")

st.info(
    "RainWise evaluates rainwater harvesting using historical "
    "precipitation or sample CSV data. Water demand rates are "
    "illustrative assumptions."
)

# --------------------------------------------------
# 1. Location and rainfall
# --------------------------------------------------

st.header("1. Location & Rainfall")

rainfall_source = st.radio(
    "Select rainfall data source",
    [
        "Historical Weather API",
        "7-Day Sample CSV",
        "Upload CSV",
    ],
    horizontal=True,
)

selected_lat = None
selected_lon = None
uploaded_file = None

if rainfall_source == "Historical Weather API":

    st.write(
        "Click a location on the map to retrieve historical "
        "daily precipitation."
    )

    if "selected_location" not in st.session_state:
        st.session_state.selected_location = None

    rain_map = folium.Map(
        location=[1.3521, 103.8198],
        zoom_start=11,
    )

    if st.session_state.selected_location:
        folium.Marker(
            location=st.session_state.selected_location,
            tooltip="Selected location",
        ).add_to(rain_map)

    map_result = st_folium(
        rain_map,
        height=430,
        width=None,
        key="rainwise_location_map",
        returned_objects=["last_clicked"],
    )

    if map_result and map_result.get("last_clicked"):
        clicked = map_result["last_clicked"]
        st.session_state.selected_location = (
            clicked["lat"],
            clicked["lng"],
        )

    if st.session_state.selected_location:
        selected_lat, selected_lon = (
            st.session_state.selected_location
        )

        c1, c2 = st.columns(2)
        c1.metric("Latitude", f"{selected_lat:.5f}")
        c2.metric("Longitude", f"{selected_lon:.5f}")
    else:
        st.warning("Select a location on the map first.")

    historical_days = st.selectbox(
        "Historical simulation period",
        [7, 30, 90],
        index=1,
        format_func=lambda n: f"{n} days",
    )

elif rainfall_source == "7-Day Sample CSV":
    st.success("Using the built-in 7-day sample rainfall data.")

else:
    uploaded_file = st.file_uploader(
        "Upload CSV with day and rainfall_mm columns",
        type=["csv"],
    )

# --------------------------------------------------
# 2. Household configuration
# --------------------------------------------------

st.header("2. Household Configuration")

left, right = st.columns(2)

with left:
    roof_area = st.number_input(
        "Roof Collection Area (m²)",
        min_value=0.0,
        value=20.0,
    )

    tank_capacity = st.number_input(
        "Tank Capacity (L)",
        min_value=1.0,
        value=500.0,
    )

    initial_storage = st.number_input(
        "Initial Storage (L)",
        min_value=0.0,
        max_value=float(tank_capacity),
        value=min(100.0, float(tank_capacity)),
    )

with right:
    efficiency = st.slider(
        "Collection Efficiency",
        min_value=0.0,
        max_value=1.0,
        value=0.8,
        step=0.05,
    )

    reserve = st.number_input(
        "Reserve Target (L)",
        min_value=0.0,
        max_value=float(tank_capacity),
        value=min(20.0, float(tank_capacity)),
    )

# --------------------------------------------------
# 3. Household water demand
# --------------------------------------------------

st.header("3. Household Water Usage")

usage_left, usage_right = st.columns(2)

with usage_left:
    garden_enabled = st.checkbox(
        "Garden Irrigation",
        value=True,
    )

    plant_type = st.selectbox(
        "Plant Type",
        ["vegetables", "flowers", "trees"],
        disabled=not garden_enabled,
    )

    garden_area = st.number_input(
        "Garden Area (m²)",
        min_value=0.0,
        value=20.0,
        disabled=not garden_enabled,
    )

    lawn_enabled = st.checkbox(
        "Lawn Irrigation",
        value=True,
    )

    lawn_area = st.number_input(
        "Lawn Area (m²)",
        min_value=0.0,
        value=10.0,
        disabled=not lawn_enabled,
    )

with usage_right:
    toilet_enabled = st.checkbox(
        "Toilet Flushing",
        value=True,
    )

    people = st.number_input(
        "Household Members",
        min_value=0,
        value=2,
        step=1,
        disabled=not toilet_enabled,
    )

demand = calculate_total_demand(
    garden_area=garden_area if garden_enabled else 0,
    plant_type=plant_type,
    lawn_area=lawn_area if lawn_enabled else 0,
    people=int(people) if toilet_enabled else 0,
)

primary_demand = demand["toilet_l"]
secondary_demand = demand["garden_l"] + demand["lawn_l"]

d1, d2, d3 = st.columns(3)

d1.metric("Primary Demand", f"{primary_demand:.1f} L/day")
d2.metric("Secondary Demand", f"{secondary_demand:.1f} L/day")
d3.metric("Total Demand", f"{demand['total_l']:.1f} L/day")

st.caption(
    "Toilet flushing is prioritised in the simulation. "
    "Garden and lawn irrigation are secondary uses."
)

# --------------------------------------------------
# 4. Simulation
# --------------------------------------------------

st.header("4. Rainwater Simulation")

if st.button("Run Simulation", type="primary"):

    try:
        dates = None

        if rainfall_source == "Historical Weather API":

            if selected_lat is None or selected_lon is None:
                st.warning("Please select a location on the map.")
                st.stop()

            with st.spinner("Retrieving historical rainfall data..."):
                weather_data = get_historical_rainfall(
                    selected_lat,
                    selected_lon,
                    days=historical_days,
                )

            rainfall = weather_data["rainfall_mm"]
            dates = weather_data["dates"]

            st.caption(
                "Weather source: "
                + weather_data["source"]
                + ". Historical precipitation is not a forecast."
            )

        elif rainfall_source == "7-Day Sample CSV":

            rainfall = load_rainfall_csv(
                BASE_DIR / "data" / "rainfall_7days.csv"
            )

        else:
            if uploaded_file is None:
                st.warning("Please upload a rainfall CSV.")
                st.stop()

            # Works with the previously updated file-like CSV loader.
            uploaded_file.seek(0)
            rainfall = load_rainfall_csv(uploaded_file)

        results = simulate_period(
            rainfall_mm=rainfall,
            initial_storage_l=initial_storage,
            roof_area_m2=roof_area,
            efficiency=efficiency,
            tank_capacity_l=tank_capacity,
            primary_demand_l=primary_demand,
            secondary_demand_l=secondary_demand,
            reserve_l=reserve,
        )

        df = pd.DataFrame(results)

        if dates is not None:
            df.insert(1, "date", dates)

        st.success("Simulation completed successfully!")

        total_collected = df["collected_l"].sum()
        total_overflow = df["overflow_l"].sum()
        total_external = df["external_supply_l"].sum()
        total_shortage = df["secondary_shortage_l"].sum()
        final_storage = df["end_l"].iloc[-1]

        st.subheader("Simulation Summary")

        m1, m2, m3 = st.columns(3)
        m1.metric("Collected Water", f"{total_collected:.1f} L")
        m2.metric("Overflow", f"{total_overflow:.1f} L")
        m3.metric("Final Storage", f"{final_storage:.1f} L")

        m4, m5 = st.columns(2)
        m4.metric("External Supply", f"{total_external:.1f} L")
        m5.metric("Secondary Shortage", f"{total_shortage:.1f} L")

        st.subheader("Daily Tank Storage")

        chart_index = "date" if dates is not None else "day"

        st.line_chart(
            df.set_index(chart_index)[["start_l", "end_l"]]
        )

        st.subheader("Daily Simulation Records")

        st.dataframe(
            df.round(2),
            use_container_width=True,
        )

        st.download_button(
            "Download Results (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="rainwise_results.csv",
            mime="text/csv",
        )

    except (
        ValueError,
        TypeError,
        FileNotFoundError,
        RuntimeError,
    ) as error:
        st.error(f"Simulation failed: {error}")

st.divider()
st.caption("RainWise | INT6181 Applied Programming with Python")
