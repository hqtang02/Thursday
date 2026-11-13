
import folium
import streamlit as st
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

st.title("Location & Rainfall")
st.caption(
    "Select a location to analyse local historical rainfall."
)

if "location_permission_requested" not in st.session_state:
    st.session_state.location_permission_requested = False

if "selected_location" not in st.session_state:
    st.session_state.selected_location = None

# -----------------------------------
# 1. Current location
# -----------------------------------

st.subheader("Choose Your Location")

st.write(
    "Use your current location or select a point manually on the map."
)

if st.button("📍 Use My Current Location"):
    st.session_state.location_permission_requested = True

if st.session_state.location_permission_requested:

    st.caption(
        "Your browser may ask for permission to access your location."
    )

    position = streamlit_geolocation()

    if position:
        latitude = position.get("latitude")
        longitude = position.get("longitude")

        if latitude is not None and longitude is not None:

            new_location = (float(latitude), float(longitude))

            if st.session_state.selected_location != new_location:
                st.session_state.selected_location = new_location
                st.session_state.simulation_result = None
                st.session_state.simulation_config = None

            st.success("Current location received.")

# -----------------------------------
# 2. Map selection
# -----------------------------------

st.subheader("Or Select on Map")

location = st.session_state.selected_location

m = folium.Map(
    location=location or [1.3521, 103.8198],
    zoom_start=11
)

if location:
    folium.Marker(
        location=location,
        tooltip="Selected Location"
    ).add_to(m)

map_data = st_folium(
    m,
    height=460,
    width=None,
    key="rainwise_map",
    returned_objects=["last_clicked"]
)

if map_data and map_data.get("last_clicked"):

    clicked = map_data["last_clicked"]

    new_location = (
        float(clicked["lat"]),
        float(clicked["lng"])
    )

    if st.session_state.selected_location != new_location:
        st.session_state.selected_location = new_location
        st.session_state.simulation_result = None
        st.session_state.simulation_config = None

# -----------------------------------
# 3. Location information
# -----------------------------------

location = st.session_state.selected_location

if location:

    st.success("Location selected successfully.")

    c1, c2 = st.columns(2)

    c1.metric("Latitude", f"{location[0]:.5f}")
    c2.metric("Longitude", f"{location[1]:.5f}")

else:
    st.info("Please select a location to continue.")

# -----------------------------------
# 4. Historical rainfall period
# -----------------------------------

st.divider()

st.subheader("Rainfall Analysis Period")

days = st.selectbox(
    "Select historical data period",
    [7, 30, 90],
    key="historical_days",
    format_func=lambda x: f"Last {x} historical days"
)

st.caption(
    "Rainfall data will be retrieved from Open-Meteo "
    "when you run the simulation. This is historical "
    "data, not a future weather forecast."
)

st.divider()

if st.button(
    "Continue to Configuration",
    type="primary",
    disabled=location is None
):
    st.switch_page("pages/configuration.py")
