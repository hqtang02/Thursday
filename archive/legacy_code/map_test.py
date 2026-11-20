
import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(
    page_title="RainWise Map Test",
    layout="wide"
)

st.title("RainWise - Location Selection")

st.write("Click a location on the map.")

m = folium.Map(
    location=[1.3521, 103.8198],
    zoom_start=11
)

map_data = st_folium(
    m,
    height=500,
    key="rainwise_map"
)

if map_data and map_data.get("last_clicked"):
    latitude = map_data["last_clicked"]["lat"]
    longitude = map_data["last_clicked"]["lng"]

    st.success("Location selected!")

    st.write("Latitude:", latitude)
    st.write("Longitude:", longitude)
else:
    st.info("Please select a location on the map.")
