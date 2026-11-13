
import streamlit as st

st.set_page_config(
    page_title="RainWise",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize shared application state
defaults = {
    "selected_location": None,
    "selected_place": None,
    "rainfall_source": "7-Day Sample CSV",
    "historical_days": 30,
    "roof_area": 20.0,
    "tank_capacity": 500.0,
    "initial_storage": 100.0,
    "efficiency": 0.8,
    "reserve": 20.0,
    "garden_enabled": True,
    "plant_type": "vegetables",
    "garden_area": 20.0,
    "lawn_enabled": True,
    "lawn_area": 10.0,
    "toilet_enabled": True,
    "people": 2,
    "simulation_result": None,
    "simulation_config": None,
    "uploaded_rainfall": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

st.sidebar.title("💧 RainWise")
st.sidebar.caption("Smart Rainwater Planning")

overview = st.Page(
    "pages/overview.py",
    title="Overview",
    icon=":material/dashboard:",
    default=True
)

location = st.Page(
    "pages/location.py",
    title="Location & Rainfall",
    icon=":material/location_on:"
)

configuration = st.Page(
    "pages/configuration.py",
    title="Configuration",
    icon=":material/tune:"
)

analysis = st.Page(
    "pages/analysis.py",
    title="Analysis",
    icon=":material/analytics:"
)

navigation = st.navigation([
    overview,
    location,
    configuration,
    analysis
])

navigation.run()

st.sidebar.divider()
st.sidebar.caption("INT6181 Python Group Project")

