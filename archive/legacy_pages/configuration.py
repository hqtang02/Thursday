
from pathlib import Path

import pandas as pd
import streamlit as st

from calculator import simulate_period
from water_demand import calculate_total_demand
from weather_api import get_historical_rainfall

from theme import inject_theme, page_header, render_sidebar


inject_theme()
render_sidebar("configuration")

page_header(
    "Household Configuration",
    "Configure your household and generate a rainwater allocation plan.",
)

# --------------------------------------------------
# 1. Check selected location
# --------------------------------------------------

location = st.session_state.get("selected_location")

if location is None:
    st.warning(
        "Please select a location before configuring your household."
    )

    if st.button("Select Location", type="primary"):
        st.switch_page("pages/location.py")

    st.stop()

c1, c2 = st.columns(2)

c1.metric("Latitude", f"{location[0]:.5f}")
c2.metric("Longitude", f"{location[1]:.5f}")


# --------------------------------------------------
# 2. Household configuration form
# --------------------------------------------------

with st.form("rainwise_configuration"):

    st.subheader("Rainwater Collection")

    left, right = st.columns(2)

    with left:
        roof_area = st.number_input(
            "Roof Collection Area (m²)",
            min_value=0.0,
            value=float(st.session_state.get("roof_area", 20.0))
        )

    with right:
        tank_capacity = st.number_input(
            "Tank Capacity (L)",
            min_value=1.0,
            value=float(st.session_state.get("tank_capacity", 500.0))
        )

    with st.expander("Advanced Collection Settings"):

        initial_storage = st.number_input(
            "Initial Storage (L)",
            min_value=0.0,
            value=float(st.session_state.get("initial_storage", 100.0))
        )

        efficiency = st.slider(
            "Collection Efficiency",
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.get("efficiency", 0.8)),
            step=0.05
        )

        reserve = st.number_input(
            "Reserve Target (L)",
            min_value=0.0,
            value=float(st.session_state.get("reserve", 20.0))
        )

    st.divider()

    st.subheader("Household Water Usage")

    garden_enabled = st.checkbox(
        "Garden Irrigation",
        value=st.session_state.get("garden_enabled", True)
    )

    garden_area = st.number_input(
        "Garden Area (m²)",
        min_value=0.0,
        value=float(st.session_state.get("garden_area", 20.0)),
        disabled=not garden_enabled
    )

    plant_types = ["vegetables", "flowers", "trees"]

    selected_plant = st.session_state.get(
        "plant_type", "vegetables"
    )

    plant_type = st.selectbox(
        "Plant Type",
        plant_types,
        index=plant_types.index(selected_plant),
        disabled=not garden_enabled
    )

    lawn_enabled = st.checkbox(
        "Lawn Irrigation",
        value=st.session_state.get("lawn_enabled", True)
    )

    lawn_area = st.number_input(
        "Lawn Area (m²)",
        min_value=0.0,
        value=float(st.session_state.get("lawn_area", 10.0)),
        disabled=not lawn_enabled
    )

    toilet_enabled = st.checkbox(
        "Toilet Flushing",
        value=st.session_state.get("toilet_enabled", True)
    )

    people = st.number_input(
        "Household Members",
        min_value=0,
        value=int(st.session_state.get("people", 2)),
        step=1,
        disabled=not toilet_enabled
    )

    submitted = st.form_submit_button(
        "Generate Water Allocation Plan",
        type="primary",
        use_container_width=True
    )


# --------------------------------------------------
# 3. Run simulation
# --------------------------------------------------

if submitted:

    # Validate tank parameters
    if initial_storage > tank_capacity:
        st.error(
            "Initial storage cannot exceed tank capacity."
        )
        st.stop()

    if reserve > tank_capacity:
        st.error(
            "Reserve target cannot exceed tank capacity."
        )
        st.stop()

    config = {
        "roof_area": roof_area,
        "tank_capacity": tank_capacity,
        "initial_storage": initial_storage,
        "efficiency": efficiency,
        "reserve": reserve,
        "garden_enabled": garden_enabled,
        "garden_area": garden_area,
        "plant_type": plant_type,
        "lawn_enabled": lawn_enabled,
        "lawn_area": lawn_area,
        "toilet_enabled": toilet_enabled,
        "people": people,
    }

    # Save configuration
    for key, value in config.items():
        st.session_state[key] = value

    # Invalidate previous results
    st.session_state.simulation_result = None
    st.session_state.simulation_config = None

    try:

        # ---------------------------------------
        # Calculate household water demand
        # ---------------------------------------

        demand = calculate_total_demand(
            garden_area=(
                garden_area if garden_enabled else 0
            ),
            plant_type=plant_type,
            lawn_area=(
                lawn_area if lawn_enabled else 0
            ),
            people=(
                int(people) if toilet_enabled else 0
            )
        )

        # ---------------------------------------
        # Retrieve historical rainfall
        # ---------------------------------------

        source = "Historical Weather API"

        location = st.session_state.get(
            "selected_location"
        )

        if location is None:
            st.error(
                "Please select your location first."
            )
            st.stop()

        with st.spinner(
            "Retrieving local historical rainfall..."
        ):

            weather = get_historical_rainfall(
                location[0],
                location[1],
                days=st.session_state.get(
                    "historical_days", 30
                )
            )

        rainfall = weather["rainfall_mm"]
        dates = weather["dates"]

        # ---------------------------------------
        # Simulate daily water allocation
        # ---------------------------------------

        records = simulate_period(
            rainfall_mm=rainfall,
            initial_storage_l=initial_storage,
            roof_area_m2=roof_area,
            efficiency=efficiency,
            tank_capacity_l=tank_capacity,
            primary_demand_l=demand["toilet_l"],
            secondary_demand_l=(
                demand["garden_l"]
                + demand["lawn_l"]
            ),
            reserve_l=reserve
        )

        df = pd.DataFrame(records)

        if df.empty:
            raise ValueError(
                "The simulation returned no daily records."
            )

        if dates is not None:
            df.insert(1, "date", dates)

        # ---------------------------------------
        # Calculate summary
        # ---------------------------------------

        summary = {
            "collected": float(
                df["collected_l"].sum()
            ),
            "overflow": float(
                df["overflow_l"].sum()
            ),
            "external": float(
                df["external_supply_l"].sum()
            ),
            "shortage": float(
                df["secondary_shortage_l"].sum()
            ),
            "final_storage": float(
                df["end_l"].iloc[-1]
            )
        }

        # ---------------------------------------
        # Save results
        # ---------------------------------------

        st.session_state.simulation_result = {
            "data": df,
            "summary": summary,
            "source": source
        }

        st.session_state.simulation_config = {
            **config,
            "rainfall_source": source,
            "selected_location": location,
            "historical_days": st.session_state.get(
                "historical_days", 30
            )
        }

        # ---------------------------------------
        # Automatically open allocation plan
        # ---------------------------------------

        st.switch_page("pages/analysis.py")

    except Exception as error:
        st.error(
            f"Simulation failed: {error}"
        )
