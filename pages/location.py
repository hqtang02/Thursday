import folium
import streamlit as st
from geonamescache import GeonamesCache
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

from theme import inject_theme, page_header, render_sidebar

DEFAULT_CENTER = (22.3193, 114.1694)  # Hong Kong

# Region labels for Hong Kong (geonamescache only provides US state names).
HK_REGION_NAMES = {
    "HCW": "Central and Western",
    "HKC": "Central",
    "HKE": "Eastern",
    "HKW": "Wan Chai",
    "KKC": "Kowloon City",
    "KSS": "Sham Shui Po",
    "KWT": "Wong Tai Sin",
    "NKT": "Kwai Tsing",
    "NST": "Sha Tin",
    "NSK": "Sai Kung",
    "NTM": "Tuen Mun",
    "NTP": "New Territories",
    "NTW": "Tsuen Wan",
    "NYL": "Yuen Long",
}


@st.cache_resource
def get_geo_cache():
    return GeonamesCache()


def reset_simulation():
    st.session_state.simulation_result = None
    st.session_state.simulation_config = None


def set_location(latitude, longitude, place, source):
    st.session_state.selected_location = (float(latitude), float(longitude))
    st.session_state.selected_place = place
    st.session_state.location_source = source
    reset_simulation()


inject_theme()
render_sidebar("location")

page_header(
    "Location & Rainfall",
    "Select a location to analyse local historical rainfall.",
)

for key, value in {
    "selected_location": None,
    "selected_place": None,
    "location_source": None,
    "location_permission_requested": False,
    "last_map_click": None,
    "last_city_key": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

gc = get_geo_cache()
countries = gc.get_countries()
country_codes = sorted(countries, key=lambda code: countries[code]["name"])

# -----------------------------------
# 1. Country -> State / Region -> City
# -----------------------------------

st.subheader("Find a City")
st.caption(
    "Choose a country, state/region, and city. "
    "For countries without state names in the dataset, region codes are shown."
)

col1, col2, col3 = st.columns(3)

with col1:
    country_code = st.selectbox(
        "Country",
        country_codes,
        index=country_codes.index("HK") if "HK" in country_codes else 0,
        key="geo_country_code",
        format_func=lambda code: countries[code]["name"],
    )

with col2:
    country_cities = [
        city for city in gc.get_cities().values()
        if city.get("countrycode") == country_code
    ]

    region_names = {}
    if country_code == "US":
        us_states = gc.get_us_states()
        for city in country_cities:
            code = str(city.get("admin1code") or "")
            region_names[code] = us_states.get(code, {}).get("name", f"Region {code}")
    else:
        for city in country_cities:
            code = str(city.get("admin1code") or "")
            if country_code == "HK":
                region_names[code] = HK_REGION_NAMES.get(code, f"Region {code}" if code else "All regions")
            else:
                region_names[code] = f"Region {code}" if code else "All regions"

    region_codes = sorted(region_names, key=lambda code: region_names[code])
    if region_codes:
        default_region_index = (
            region_codes.index("NTP")
            if country_code == "HK" and "NTP" in region_codes
            else 0
        )
        region_code = st.selectbox(
            "State / Region",
            region_codes,
            index=default_region_index,
            key=f"geo_region_{country_code}",
            format_func=lambda code: region_names[code],
        )
    else:
        region_code = ""
        st.selectbox("State / Region", ["No region data available"], disabled=True)

with col3:
    region_cities = [
        city for city in country_cities
        if str(city.get("admin1code") or "") == region_code
    ]
    region_cities.sort(key=lambda city: city.get("population") or 0, reverse=True)
    city_lookup = {city["geonameid"]: city for city in region_cities}

    if city_lookup:
        city_ids = list(city_lookup)
        default_city_index = 0
        if country_code == "HK" and region_code == "NTP":
            for index, city_id in enumerate(city_ids):
                if city_lookup[city_id]["name"] == "Tai Po":
                    default_city_index = index
                    break

        selected_city_id = st.selectbox(
            "City",
            city_ids,
            index=default_city_index,
            key=f"geo_city_{country_code}_{region_code}",
            format_func=lambda gid: (
                f"{city_lookup[gid]['name']} "
                f"({int(city_lookup[gid].get('population') or 0):,})"
            ),
        )
    else:
        selected_city_id = None
        st.selectbox("City", ["No city data available"], disabled=True)

if selected_city_id is not None:
    selected_city = city_lookup[selected_city_id]
    city_key = str(selected_city_id)
    if st.session_state.get("last_city_key") != city_key:
        region_name = region_names.get(region_code, "All regions")
        country_name = countries[country_code]["name"]
        place = f"{selected_city['name']}, {region_name}, {country_name}"
        set_location(
            selected_city["latitude"],
            selected_city["longitude"],
            place,
            "city",
        )
        st.session_state.last_city_key = city_key

# -----------------------------------
# 2. Current location
# -----------------------------------

st.divider()
st.subheader("Or Use Your Current Location")

if st.button("📍 Use My Current Location"):
    st.session_state.location_permission_requested = True

if st.session_state.location_permission_requested:
    st.caption("Your browser may ask for permission to access your location.")
    position = streamlit_geolocation()

    if position:
        latitude = position.get("latitude")
        longitude = position.get("longitude")

        if latitude is not None and longitude is not None:
            set_location(
                latitude,
                longitude,
                f"Current location ({float(latitude):.5f}, {float(longitude):.5f})",
                "current",
            )
            st.session_state.location_permission_requested = False
            st.rerun()

# -----------------------------------
# 3. Map selection (any point)
# -----------------------------------

st.divider()
st.subheader("Or Click Any Point on the Map")
st.caption("Click anywhere to use an arbitrary latitude and longitude.")

location = st.session_state.selected_location
selected_place = st.session_state.selected_place

m = folium.Map(
    location=list(location) if location else list(DEFAULT_CENTER),
    zoom_start=11 if location else 10,
)

if location:
    folium.Marker(
        location=list(location),
        tooltip=selected_place or "Selected location",
    ).add_to(m)

map_data = st_folium(
    m,
    height=460,
    width=None,
    key="rainwise_map",
    returned_objects=["last_clicked"],
)

if map_data and map_data.get("last_clicked"):
    clicked = map_data["last_clicked"]
    latitude = float(clicked["lat"])
    longitude = float(clicked["lng"])
    click_key = (round(latitude, 6), round(longitude, 6))

    if st.session_state.get("last_map_click") != click_key:
        st.session_state.last_map_click = click_key
        set_location(
            latitude,
            longitude,
            f"Custom point ({latitude:.5f}, {longitude:.5f})",
            "map",
        )
        st.rerun()

# -----------------------------------
# 4. Selected location information
# -----------------------------------

location = st.session_state.selected_location
selected_place = st.session_state.selected_place

if location:
    st.success(f"{selected_place}  |  {location[0]:.5f}, {location[1]:.5f}")

    c1, c2 = st.columns(2)
    c1.metric("Latitude", f"{location[0]:.5f}")
    c2.metric("Longitude", f"{location[1]:.5f}")
    st.caption(f"Location source: {st.session_state.location_source}")
else:
    st.info("Choose a city, click the map, or use your current location.")

# -----------------------------------
# 5. Historical rainfall period
# -----------------------------------

st.divider()
st.subheader("Rainfall Analysis Period")

st.selectbox(
    "Select historical data period",
    [7, 30, 90],
    key="historical_days",
    format_func=lambda days: f"Last {days} historical days",
)

st.caption(
    "Rainfall data will be retrieved from Open-Meteo when you run the simulation. "
    "This is historical data, not a future weather forecast."
)

st.divider()

if st.button(
    "Continue to Configuration",
    type="primary",
    disabled=location is None,
):
    st.switch_page("pages/configuration.py")
