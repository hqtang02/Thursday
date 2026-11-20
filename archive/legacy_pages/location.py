import folium
import streamlit as st
from geonamescache import GeonamesCache
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

from theme import inject_theme, page_header, render_sidebar
from weather_api import get_historical_rainfall

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


@st.cache_data(ttl=3600, show_spinner=False)
def get_period_averages(latitude, longitude):
    data = get_historical_rainfall(latitude, longitude, days=90)
    values = data.get("rainfall_mm", [])
    if not values:
        raise ValueError("No rainfall data returned.")
    return {
        days: round(sum(values[-days:]) / len(values[-days:]), 2)
        for days in (7, 30, 90)
    }


def rain_intensity(average_mm):
    if average_mm is None:
        return "rw-rain-light", "Rain data unavailable"
    if average_mm < 2.0:
        return "rw-rain-light", "Light rain"
    if average_mm < 8.0:
        return "rw-rain-moderate", "Moderate rain"
    return "rw-rain-heavy", "Heavy rain"


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

if "historical_days" not in st.session_state:
    st.session_state.historical_days = 30

days_query = st.query_params.get("days")
if isinstance(days_query, list):
    days_query = days_query[0] if days_query else None
if days_query in {"7", "30", "90"}:
    st.session_state.historical_days = int(days_query)
    st.query_params.clear()

st.write("Select historical data period")
st.caption("Hover over an option to preview its rainfall window and intensity.")

if location:
    with st.spinner("Reading average rainfall for each period..."):
        try:
            period_averages = get_period_averages(location[0], location[1])
        except Exception:
            period_averages = {7: None, 30: None, 90: None}
else:
    period_averages = {7: None, 30: None, 90: None}

period_css = """
<style>
  [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    overflow-x: hidden !important;
  }

  .rw-period-select {
    width: 100%;
    max-width: 340px;
  }

  .rw-period-select details {
    position: relative;
    width: 100%;
  }

  .rw-period-select summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.75rem 0.9rem;
    border: 1px solid var(--rw-line);
    border-radius: 10px;
    background: var(--rw-surface);
    color: var(--rw-ink);
    cursor: pointer;
    list-style: none;
  }

  .rw-period-select summary::-webkit-details-marker {
    display: none;
  }

  .rw-period-select details[open] summary {
    border-color: var(--rw-mint);
    box-shadow: 0 0 0 2px rgba(106, 211, 190, 0.18);
  }

  .rw-period-chevron {
    color: var(--rw-muted);
    font-size: 1.1rem;
    line-height: 1;
  }

  .rw-period-menu {
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    left: 0;
    z-index: 100;
    overflow: visible;
    padding: 0.35rem;
    border: 1px solid var(--rw-line);
    border-radius: 12px;
    background: var(--rw-surface);
    box-shadow: 0 16px 36px rgba(9, 50, 38, 0.16);
  }

  .rw-period-option {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.7rem 0.6rem;
    border-radius: 8px;
    color: var(--rw-ink) !important;
    text-decoration: none !important;
  }

  .rw-period-option:hover,
  .rw-period-option.active {
    background: #edf8d8;
    color: var(--rw-green) !important;
    font-weight: 700;
  }

  .rw-rain-tip {
    position: absolute;
    top: 50%;
    left: calc(100% + 12px);
    z-index: 200;
    width: 240px;
    min-height: 200px;
    padding: 0.8rem;
    overflow: hidden;
    border: 1px solid rgba(198, 243, 107, 0.3);
    border-radius: 14px;
    background: linear-gradient(145deg, #0e4a36, #082f24);
    color: #ffffff;
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    transform: translateY(-50%);
    transition: opacity 140ms ease, visibility 140ms ease;
    box-shadow: 0 16px 34px rgba(9, 50, 38, 0.24);
  }

  .rw-period-option:hover .rw-rain-tip {
    opacity: 1;
    visibility: visible;
  }

  .rw-rain-tip-label {
    display: block;
    margin-bottom: 0.55rem;
    color: rgba(255, 255, 255, 0.72);
    font-size: 0.72rem;
    letter-spacing: 0.06em;
    text-align: center;
    text-transform: uppercase;
  }

  .rw-rain-scene {
    position: relative;
    width: 100%;
    height: 126px;
    overflow: hidden;
    border-radius: 12px;
    background: linear-gradient(180deg, #143f34, #0a2d26);
  }

  .rw-rain-svg {
    display: block;
    width: 170px;
    height: 120px;
    margin: 0 auto;
  }

  .rw-svg-cloud {
    fill: none;
    stroke: #d8f5b0;
    stroke-width: 7;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .rw-rain-line {
    stroke: #2bc7f2;
    stroke-width: 8;
    stroke-linecap: round;
    opacity: 0;
    animation: rw-svg-fall 1.0s linear infinite;
    transform-box: fill-box;
    transform-origin: center;
  }

  .rw-rain-line:nth-of-type(1) { animation-delay: -0.15s; }
  .rw-rain-line:nth-of-type(2) { animation-delay: -0.55s; }
  .rw-rain-line:nth-of-type(3) { animation-delay: -0.30s; }
  .rw-rain-line:nth-of-type(4) { animation-delay: -0.75s; }
  .rw-rain-line:nth-of-type(5) { animation-delay: -0.05s; }
  .rw-rain-line:nth-of-type(6) { animation-delay: -0.45s; }
  .rw-rain-line:nth-of-type(7) { animation-delay: -0.20s; }
  .rw-rain-line:nth-of-type(8) { animation-delay: -0.65s; }

  .rw-rain-tip.rw-rain-light .rw-rain-line {
    stroke: rgba(87, 215, 245, 0.72);
    stroke-width: 7;
    animation-duration: 1.6s;
  }

  .rw-rain-tip.rw-rain-light .rw-rain-line:nth-of-type(n+5) {
    display: none;
  }

  .rw-rain-tip.rw-rain-moderate .rw-rain-line {
    stroke: #2bc7f2;
    stroke-width: 8;
    animation-duration: 0.9s;
  }

  .rw-rain-tip.rw-rain-moderate .rw-rain-line:nth-of-type(n+7) {
    display: none;
  }

  .rw-rain-tip.rw-rain-heavy .rw-rain-scene {
    background: linear-gradient(180deg, #09251f, #051713);
  }

  .rw-rain-tip.rw-rain-heavy .rw-rain-line {
    stroke: #35d7ff;
    stroke-width: 9;
    animation-duration: 0.45s;
  }

  .rw-rain-tip.rw-rain-heavy .rw-rain-scene:after {
    content: "⚡";
    position: absolute;
    right: 18px;
    bottom: 8px;
    color: #d8f5b0;
    font-size: 1.1rem;
    animation: rw-lightning 1.8s ease-in-out infinite;
  }

  .rw-rain-tip-footer {
    display: block;
    margin-top: 0.45rem;
    color: #c6f36b;
    font-size: 0.78rem;
    font-weight: 700;
    text-align: center;
  }

  @keyframes rw-svg-fall {
    0% { opacity: 0; transform: translateY(-6px); }
    20% { opacity: 1; }
    100% { opacity: 0; transform: translateY(10px); }
  }

  @keyframes rw-lightning {
    0%, 65%, 100% { opacity: 0.15; }
    70%, 74% { opacity: 1; }
    78% { opacity: 0.2; }
  }

  @media (max-width: 900px) {
    .rw-rain-tip {
      top: auto;
      right: 0;
      bottom: calc(100% + 8px);
      left: auto;
      transform: none;
    }
  }
</style>
"""

rain_svg = """
<svg class="rw-rain-svg" viewBox="0 0 200 140" aria-hidden="true">
  <path class="rw-svg-cloud" d="M50 88 C36 88 28 77 31 65 C34 53 47 48 58 54 C61 34 78 22 97 28 C113 18 136 27 140 48 C156 46 168 57 167 70 C166 82 155 89 143 89 L57 89 C54 89 51 89 50 88 Z"/>
  <line class="rw-rain-line" x1="62" y1="96" x2="62" y2="116"/>
  <line class="rw-rain-line" x1="82" y1="92" x2="82" y2="122"/>
  <line class="rw-rain-line" x1="102" y1="98" x2="102" y2="114"/>
  <line class="rw-rain-line" x1="122" y1="94" x2="122" y2="126"/>
  <line class="rw-rain-line" x1="72" y1="102" x2="72" y2="118"/>
  <line class="rw-rain-line" x1="112" y1="100" x2="112" y2="120"/>
  <line class="rw-rain-line" x1="92" y1="104" x2="92" y2="116"/>
  <line class="rw-rain-line" x1="132" y1="98" x2="132" y2="114"/>
</svg>
"""

period_options = []
for days in (7, 30, 90):
    active = "active" if st.session_state.historical_days == days else ""
    avg = period_averages.get(days)
    intensity_class, intensity_label = rain_intensity(avg)
    avg_label = f"{avg:.1f} mm/day" if avg is not None else "data unavailable"
    period_options.append(
        f'<a class="rw-period-option {active}" href="?days={days}" target="_self">'
        f'<span>Last {days} historical days</span>'
        f'<span class="rw-rain-tip {intensity_class}">'
        f'<span class="rw-rain-tip-label">{days}-day window · {avg_label}</span>'
        '<span class="rw-rain-scene">'
        + rain_svg
        + '</span>'
        f'<span class="rw-rain-tip-footer">{intensity_label}</span>'
        '</span>'
        '</a>'
    )

selected_label = f"Last {st.session_state.historical_days} historical days"
period_html = (
    period_css
    + '<div class="rw-period-select"><details>'
    + f'<summary><span>{selected_label}</span><span class="rw-period-chevron">⌄</span></summary>'
    + '<div class="rw-period-menu">'
    + "".join(period_options)
    + '</div></details></div>'
)
st.markdown(period_html, unsafe_allow_html=True)

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
