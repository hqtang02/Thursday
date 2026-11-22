
import html
from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit.components.v2 import component

try:
    from streamlit_js_eval import get_geolocation
except ImportError:  # fallback to the already-installed streamlit-geolocation package
    from streamlit_geolocation import streamlit_geolocation as _streamlit_geolocation

    def get_geolocation():
        position = _streamlit_geolocation()
        if isinstance(position, dict):
            return {
                "coords": {
                    "latitude": position.get("latitude"),
                    "longitude": position.get("longitude"),
                }
            }
        return position

from rainfall_service import search_city, get_rainfall_forecast
from rainwater_engine import WaterTask, compare_strategies
from recommendation_engine import generate_recommendations


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Rainwater Smart Planner",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CARD_HEIGHT = 340

SCENES = {
    "Bathroom": ("bathroom", "🚽", 60, 1, False, "day"),
    "Kitchen": ("kitchen", "🚰", 15, 2, False, "day"),
    "Laundry": ("laundry", "🧺", 80, 3, True, "use"),
    "Garden": ("garden", "🌿", 40, 2, False, "day"),
    "Driveway": ("driveway", "🚙", 100, 4, True, "use"),
    "Living Room": ("living", "🛋️", 20, 3, False, "day"),
}

FACTORS = {
    "Low": 0.6,
    "Medium": 1.0,
    "High": 1.5,
}

st.session_state.setdefault("entered", False)
st.session_state.setdefault("location_mode", "city")
st.session_state.setdefault("selected_location", None)
st.session_state.setdefault("selected_scenes", ["Bathroom", "Garden", "Laundry"])
st.session_state.setdefault("usage_levels", {})
st.session_state.setdefault("plan", None)
st.session_state.setdefault("show_results", False)
st.session_state.setdefault("city_results", [])
st.session_state.setdefault("searched_city", "")
st.session_state.setdefault("request_location", False)

for name, config in SCENES.items():
    slug = config[0]
    st.session_state.usage_levels.setdefault(name, "Medium")
    st.session_state.setdefault(f"level_{slug}", "Medium")


# ============================================================
# CALLBACKS
# ============================================================

def invalidate_plan():
    st.session_state.plan = None


def set_efficiency_preset(value):
    st.session_state.ws_eff = value
    invalidate_plan()


def enter_app():
    st.session_state.entered = True


def return_home():
    st.session_state.entered = False


def change_location_mode(mode):
    st.session_state.location_mode = mode
    st.session_state.selected_location = None
    invalidate_plan()


def set_location(location):
    old = st.session_state.selected_location

    old_coords = None

    if old:
        old_coords = (
            float(old["latitude"]),
            float(old["longitude"]),
        )

    new_coords = (
        float(location["latitude"]),
        float(location["longitude"]),
    )

    if new_coords != old_coords:
        invalidate_plan()

    st.session_state.selected_location = location


def toggle_scene(name):
    scenes = list(st.session_state.selected_scenes)

    if name in scenes:
        scenes.remove(name)
    else:
        scenes.append(name)

    st.session_state.selected_scenes = scenes
    invalidate_plan()


def change_level(name, slug):
    st.session_state.usage_levels[name] = (
        st.session_state[f"level_{slug}"]
    )
    invalidate_plan()


def demand_for(name):
    config = SCENES[name]
    level = st.session_state.usage_levels[name]

    return round(float(config[2]) * FACTORS[level], 2)


# ============================================================
# CALCULATION
# ============================================================

def build_tasks(selected, days):
    tasks = []

    for name in selected:
        slug, icon, base, priority, flexible, unit = SCENES[name]
        amount = demand_for(name)

        if amount <= 0:
            continue

        if flexible:
            tasks.append(
                WaterTask(
                    name=name,
                    amount=amount,
                    priority=priority,
                    flexible=True,
                    earliest_day=0,
                    latest_day=days - 1,
                )
            )
        else:
            for day in range(days):
                tasks.append(
                    WaterTask(
                        name=name,
                        amount=amount,
                        priority=priority,
                        flexible=False,
                        earliest_day=day,
                        latest_day=day,
                    )
                )

    return tasks


def make_daily_table(result, dates):
    rows = []

    for record in result["records"]:
        allocations = {}

        for item in record["allocations"]:
            name = item["task"]
            allocations[name] = (
                allocations.get(name, 0) + item["supplied"]
            )

        row = {
            "Date": dates[record["day"] - 1],
            "Rainfall (mm)": record["rainfall"],
            "Collected (L)": record["collected"],
            "Allocated (L)": record["allocated"],
            "Shortage (L)": record["shortage"],
            "Overflow (L)": record["overflow"],
            "Remaining (L)": record["remaining"],
        }

        row.update(allocations)
        rows.append(row)

    return pd.DataFrame(rows).fillna(0)


@st.cache_data(ttl=1800, show_spinner=False)
def load_weather(latitude, longitude):
    dates, rainfall = get_rainfall_forecast(latitude, longitude)
    fetched = datetime.now().astimezone().isoformat(timespec="minutes")
    return dates, rainfall, fetched


def date_label(value):
    try:
        return pd.to_datetime(value).strftime("%a %d %b")
    except (ValueError, TypeError):
        return str(value)


def rain_category(rain):
    if rain < 0.1:
        return "dry", "No rain"
    if rain < 2:
        return "light", "Light rain"
    if rain < 10:
        return "moderate", "Rain expected"
    return "heavy", "High rainfall"


# ============================================================
# FULLSCREEN FAUCET COMPONENT
# ============================================================

WELCOME_HTML = """
<div id="welcome">
  <div class="welcome-center">
    <div class="brand">◈ &nbsp; RAINWATER SMART PLANNER</div>

    <h1>Make Every<br><em>Drop Count.</em></h1>

    <p>Collect, manage, and use rainwater smarter.</p>

    <svg viewBox="0 0 550 340" class="tap">
      <defs>
        <linearGradient id="metal" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#f5fdff"/>
          <stop offset="25%" stop-color="#8fa8b5"/>
          <stop offset="50%" stop-color="#e1eef3"/>
          <stop offset="78%" stop-color="#5f7a89"/>
          <stop offset="100%" stop-color="#c3d8e0"/>
        </linearGradient>
        <linearGradient id="stream" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="#269fcf"/>
          <stop offset="50%" stop-color="#efffff"/>
          <stop offset="100%" stop-color="#43bce5"/>
        </linearGradient>
      </defs>

      <rect x="65" y="118" width="65" height="110"
            rx="18" fill="url(#metal)"/>
      <rect x="95" y="137" width="190" height="68"
            rx="28" fill="url(#metal)"/>
      <rect x="240" y="95" width="86" height="112"
            rx="23" fill="url(#metal)"/>

      <path d="M290 170 H365 Q425 170 425 226 V250"
            stroke="url(#metal)" stroke-width="64"
            fill="none" stroke-linecap="round"/>

      <rect x="395" y="232" width="60" height="30"
            rx="12" fill="url(#metal)"/>
      <ellipse cx="425" cy="262" rx="26" ry="7" fill="#34515f"/>

      <g id="lever" role="slider" tabindex="0"
         aria-label="Drag tap handle to enter"
         aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
        <rect x="264" y="65" width="44" height="50"
              rx="12" fill="url(#metal)"/>
        <rect x="247" y="55" width="163" height="28"
              rx="14" fill="url(#metal)"/>
        <rect x="240" y="35" width="195" height="75"
              fill="transparent"/>
      </g>

      <rect id="tap-water" x="421" y="265"
            width="8" height="0" rx="5" fill="url(#stream)"/>
    </svg>

    <div class="help">DRAG THE HANDLE TO THE RIGHT →</div>
    <div class="track"><div id="progress"></div></div>
  </div>

  <div id="intro-water">
    <div class="intro-wave"></div>
    <div class="intro-water-body"></div>
  </div>
</div>
"""

WELCOME_CSS = """
:host {
  position: fixed !important;
  inset: 0 !important;
  z-index: 2147483000 !important;
  width: 100vw !important;
  height: 100dvh !important;
}

* { box-sizing: border-box; }

#welcome {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100dvh;
  background: radial-gradient(circle at 50% 40%, #284e60, transparent 65%),
              linear-gradient(125deg, #081923, #102d3d);
  color: white;
  font-family: Inter, "Segoe UI", Arial, sans-serif;
  overflow: hidden;
}

.welcome-center {
  position: absolute;
  inset: 0;
  z-index: 3;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 20px;
}

.brand {
  color: #8cdbe2;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 3px;
}

h1 {
  font-size: clamp(43px, 6vw, 80px);
  letter-spacing: -3px;
  line-height: 1.08;
  margin: 30px 0 13px;
}

h1 em { color: #83dce5; font-style: normal; }

p { color: #a9c5cd; }

.tap {
  width: min(550px, 92vw);
  max-height: 48vh;
  margin-top: 12px;
  overflow: visible;
  filter: drop-shadow(0 16px 15px #0005);
}

#lever {
  cursor: grab;
  touch-action: none;
  transform-origin: 286px 110px;
}

#lever:focus-visible {
  outline: none;
  filter: drop-shadow(0 0 10px #8fe8fa);
}

.help {
  margin-top: -12px;
  color: #9bd7dd;
  font-size: 11px;
  letter-spacing: 2px;
}

.track {
  height: 4px;
  width: 210px;
  background: #345968;
  margin-top: 18px;
  border-radius: 10px;
  overflow: hidden;
}

#progress {
  height: 100%;
  width: 0%;
  background: #8be8ef;
}

#intro-water {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 0%;
  z-index: 4;
  pointer-events: none;
  transition: height .08s linear;
}

.intro-water-body {
  position: absolute;
  inset: 0;
  background: linear-gradient(#91def0d9, #278caf);
}

.intro-wave {
  position: absolute;
  top: -20px;
  left: -15%;
  width: 130%;
  height: 45px;
  border-radius: 50%;
  background: #8bdeed;
  animation: welcomeWave 3s ease-in-out infinite;
}

@keyframes welcomeWave {
  50% { transform: translateX(2%) translateY(8px); }
}

#welcome.done #intro-water {
  height: 125% !important;
  transition: height .9s ease-in !important;
}

@media (prefers-reduced-motion: reduce) {
  .intro-wave { animation: none; }
}
"""

WELCOME_JS = """
export default function({parentElement, setTriggerValue}) {
  const root = parentElement.querySelector("#welcome");
  const lever = parentElement.querySelector("#lever");
  const water = parentElement.querySelector("#intro-water");
  const stream = parentElement.querySelector("#tap-water");
  const bar = parentElement.querySelector("#progress");

  if (!root || !lever) return;

  let progress = 0;
  let dragging = false;
  let finished = false;
  let startX = 0;
  let startProgress = 0;
  let timer = null;

  function update(value) {
    if (finished) return;

    progress = Math.max(0, Math.min(100, value));

    const t = progress / 100;
    const width = 6 + t * 14;

    lever.style.transform = `rotate(${t * 45}deg)`;
    lever.setAttribute("aria-valuenow", String(Math.round(progress)));

    stream.setAttribute("height", String(t * 75));
    stream.setAttribute("width", String(width));
    stream.setAttribute("x", String(425 - width / 2));

    bar.style.width = `${progress}%`;
    water.style.height = `${t * 75}%`;
  }

  function finish() {
    if (finished) return;

    update(100);
    finished = true;
    dragging = false;
    root.classList.add("done");

    timer = window.setTimeout(() => {
      setTriggerValue("enter", true);
    }, 1000);
  }

  function down(event) {
    if (finished) return;

    dragging = true;
    startX = event.clientX;
    startProgress = progress;

    lever.setPointerCapture(event.pointerId);
    event.preventDefault();
  }

  function move(event) {
    if (!dragging || finished) return;

    update(startProgress + (event.clientX - startX) / 155 * 100);

    if (progress >= 99) finish();
  }

  function up() {
    if (!dragging || finished) return;

    dragging = false;

    if (progress >= 90) finish();
    else update(0);
  }

  function key(event) {
    if (event.key === "ArrowRight") {
      event.preventDefault();
      update(progress + 20);
      if (progress >= 100) finish();
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      update(progress - 20);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      finish();
    }
  }

  lever.addEventListener("pointerdown", down);
  lever.addEventListener("pointermove", move);
  lever.addEventListener("pointerup", up);
  lever.addEventListener("pointercancel", up);
  lever.addEventListener("keydown", key);

  return () => {
    lever.removeEventListener("pointerdown", down);
    lever.removeEventListener("pointermove", move);
    lever.removeEventListener("pointerup", up);
    lever.removeEventListener("pointercancel", up);
    lever.removeEventListener("keydown", key);

    if (timer !== null) window.clearTimeout(timer);
  };
}
"""


# ============================================================
# INTRO SCREEN
# ============================================================

if not st.session_state.entered:
    st.markdown(
        """
        <style>
        html, body {overflow:hidden !important;}
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stSidebar"] {
            display:none !important;
        }
        .block-container {
            padding:0 !important;
            max-width:none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    welcome = component(
        "rainwater_welcome_html_fixed_v1",
        html=WELCOME_HTML,
        css=WELCOME_CSS,
        js=WELCOME_JS,
    )

    welcome(
        key="welcome_screen",
        on_enter_change=enter_app,
    )

    st.stop()


# ============================================================
# BACKGROUND WATER COMPONENT
# ============================================================

WATER_HTML = """
<div class="water-background" aria-hidden="true">
  <div class="water-fill">
    <div class="water-body"></div>
    <div class="water-wave wave-back"></div>
    <div class="water-wave wave-front"></div>
    <div class="reflection"></div>
    <div class="caustics"></div>
  </div>
</div>
"""

WATER_CSS = """
:host {
  position: fixed !important;
  inset: 0 !important;
  width: 100vw !important;
  height: 100dvh !important;
  z-index: 0 !important;
  pointer-events: none !important;
}

.water-background {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100dvh;
  overflow: hidden;
  pointer-events: none;
  background:
    radial-gradient(circle at 12% 10%, #c6eaf0, transparent 46%),
    radial-gradient(circle at 89% 35%, #c5eddb, transparent 42%),
    linear-gradient(150deg, #f1fafd, #e8f6f4);
}

.water-fill {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 0%;
  transition: height 1250ms cubic-bezier(.2,.7,.2,1);
}

.water-body {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 25% 16%, #e9ffff78, transparent 48%),
    linear-gradient(
      180deg,
      rgba(132,218,237,.72),
      rgba(69,171,211,.83) 50%,
      rgba(20,111,166,.9)
    );
}

.water-wave {
  position: absolute;
  z-index: 3;
  top: -20px;
  left: -15%;
  width: 130%;
  height: 62px;
  border-radius: 50%;
  animation: wave 5.4s ease-in-out infinite alternate;
}

.wave-back {
  background: #89dceabd;
  top: -27px;
}

.wave-front {
  background: #dcfafb70;
  top: -13px;
  animation-direction: alternate-reverse;
  animation-duration: 4.3s;
}

@keyframes wave {
  0% { transform: translate(-2%, -5px) rotate(-.3deg); }
  100% { transform: translate(2%, 9px) rotate(.3deg); }
}

.reflection {
  position: absolute;
  z-index: 4;
  top: -20%;
  left: 28%;
  height: 160%;
  width: 20%;
  transform: rotate(19deg);
  filter: blur(24px);
  background: linear-gradient(90deg, transparent, #ffffff35, transparent);
  animation: shine 8s ease-in-out infinite;
}

@keyframes shine {
  50% { transform: rotate(19deg) translateX(32px); }
}

.caustics {
  position: absolute;
  inset: 0;
  opacity: .18;
  background:
    repeating-radial-gradient(
      ellipse at 25% 30%,
      transparent 0,
      transparent 26px,
      #ffffff50 28px,
      transparent 35px
    );
  background-size: 360px 240px;
  animation: caustics 15s linear infinite;
}

@keyframes caustics {
  to { background-position: 360px 160px; }
}

@media (prefers-reduced-motion: reduce) {
  .water-wave, .reflection, .caustics { animation: none; }
  .water-fill { transition: none; }
}
"""

WATER_JS = """
export default function({parentElement, data}) {
  const element = parentElement.querySelector(".water-fill");
  if (!element) return;

  const level = Math.max(0, Math.min(100, Number(data?.level ?? 0)));
  const old = Number(window.__rainwaterLevel ?? 0);

  element.style.height = `${old}%`;

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      element.style.height = `${level}%`;
      window.__rainwaterLevel = level;
    });
  });
}
"""

water_background = component(
    "rainwater_water_background_fixed_v1",
    html=WATER_HTML,
    css=WATER_CSS,
    js=WATER_JS,
)

water_background(
    key="water_background",
    data={
        "level": (
            len(st.session_state.selected_scenes)
            / len(SCENES)
            * 100
        )
    },
    height=0,
)


# ============================================================
# MAIN CSS
# ============================================================

MAIN_CSS = """
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
  background: transparent !important;
}

[data-testid="stHeader"],
[data-testid="stToolbar"] {
  background: transparent !important;
}

[data-testid="stHeader"]::before {
  display: none !important;
}

[data-testid="stMainBlockContainer"] {
  position: relative;
  z-index: 1;
  max-width: 1240px;
  padding-top: 2rem;
  padding-bottom: 4rem;
}

.stApp h1,
.stApp h2,
.stApp h3 {
  color: #194e5a;
}

[class*="st-key-panel_"] {
  background: rgba(255,255,255,.88);
  border: 1px solid rgba(255,255,255,.95);
  border-radius: 24px;
  padding: 22px;
  margin-bottom: 20px;
  box-shadow: 0 12px 30px #267a8b12;
  backdrop-filter: blur(14px);
}

div[data-testid="stMetric"] {
  padding: 13px;
  background: #eaf8f9;
  border: 1px solid #d3e9ee;
  border-radius: 15px;
}

/* LOCATION CARDS */

[class*="st-key-location_option_"] button {
  position: relative !important;
  width: 100% !important;
  height: 140px !important;
  min-height: 140px !important;
  border-radius: 20px !important;
  border: 2px solid #d4e8ed !important;
  background: linear-gradient(140deg, #f3fbfc, #e9f6f4) !important;
  color: #245b69 !important;
  font-size: 18px !important;
  font-weight: 700 !important;
  display: flex !important;
  align-items: flex-end !important;
  justify-content: flex-start !important;
  padding: 19px !important;
  cursor: pointer !important;
}

[class*="st-key-location_option_"] button::before {
  position: absolute;
  top: 15px;
  left: 19px;
  font-size: 36px;
}

[class*="st-key-location_option_gps"] button::before {
  content: "📍";
}

[class*="st-key-location_option_city"] button::before {
  content: "🌍";
}

[class*="st-key-location_option_"][class*="_active"] button {
  border-color: #299cab !important;
  background: linear-gradient(145deg,#dcf5f7,#e5f7ed) !important;
}

[class*="st-key-location_option_"][class*="_active"]::after {
  content: "✓";
  position: absolute;
  z-index: 4;
  top: 14px;
  right: 14px;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  color: white;
  background: #2b9faa;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

[class*="st-key-panel_location_input"] {
  background: #f5fbfc;
  border: 1px solid #d6e8eb;
  border-radius: 19px;
  padding: 17px;
}

.location-confirmation {
  padding: 17px;
  border-radius: 16px;
  background: linear-gradient(120deg,#dff6f3,#e9f8fc);
  color: #245969;
  margin: 15px 0;
}

.location-name {
  font-size: 17px;
  font-weight: 700;
}

.location-coordinates {
  font-size: 12px;
  color: #678b95;
  margin-top: 6px;
}

/* WEATHER CARDS */

.weather-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0,1fr));
  gap: 9px;
  width: 100%;
  margin: 15px 0 8px;
}

.weather-card {
  box-sizing: border-box;
  min-width: 0;
  min-height: 198px;
  padding: 12px 7px;
  background: linear-gradient(155deg,#f0fcff,#e1f3f8);
  border: 1px solid #d0e8ee;
  border-radius: 17px;
  box-shadow: 0 6px 13px #2c849512;
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: transform .25s ease;
}

.weather-card:hover {
  transform: translateY(-4px);
}

.weather-card.heavy {
  background: linear-gradient(#e5f4fa,#cbe7f1);
  border-color: #9cd0df;
}

.weather-date {
  font-size: 11px;
  font-weight: 700;
  color: #57808d;
  white-space: nowrap;
}

.weather-visual {
  position: relative;
  height: 77px;
  width: 90px;
  margin: 9px auto 7px;
}

.cloud {
  position: absolute;
  top: 18px;
  left: 18px;
  width: 56px;
  height: 27px;
  background: #b1d8e5;
  border-radius: 20px;
  animation: floatCloud 4s ease-in-out infinite;
  filter: drop-shadow(0 4px 6px #377b9225);
}

.cloud::before,
.cloud::after {
  content: "";
  position: absolute;
  background: inherit;
  border-radius: 50%;
}

.cloud::before {
  width: 30px;
  height: 30px;
  top: -13px;
  left: 5px;
}

.cloud::after {
  width: 36px;
  height: 36px;
  top: -19px;
  left: 23px;
}

.weather-card.heavy .cloud { background: #729eaf; }
.weather-card.moderate .cloud { background: #91c1cf; }
.weather-card.dry .cloud { opacity: .6; }

.rain-drops {
  position: absolute;
  inset: 0;
}

.rain-drop {
  position: absolute;
  top: 42px;
  height: 11px;
  width: 3px;
  background: #35a9d3;
  border-radius: 50%;
  opacity: 0;
}

.rain-drop-0 { left: 24px; animation-delay: 0s !important; }
.rain-drop-1 { left: 34px; animation-delay: -.25s !important; }
.rain-drop-2 { left: 44px; animation-delay: -.5s !important; }
.rain-drop-3 { left: 54px; animation-delay: -.15s !important; }
.rain-drop-4 { left: 64px; animation-delay: -.7s !important; }
.rain-drop-5 { left: 73px; animation-delay: -.4s !important; }

.weather-card.light .rain-drop {
  animation: fallingRain 1.6s linear infinite;
}

.weather-card.moderate .rain-drop {
  animation: fallingRain 1.05s linear infinite;
}

.weather-card.heavy .rain-drop {
  animation: fallingRain .65s linear infinite;
}

.weather-card.dry .rain-drop { display: none; }
.weather-card.light .rain-drop:nth-child(n+4) { display: none; }
.weather-card.moderate .rain-drop:nth-child(n+6) { display: none; }

@keyframes fallingRain {
  0% { transform: translateY(-8px) rotate(12deg); opacity: 0; }
  25% { opacity: 1; }
  100% { transform: translateY(22px) rotate(12deg); opacity: 0; }
}

@keyframes floatCloud {
  50% { transform: translateY(-4px); }
}

.weather-amount {
  font-size: 21px;
  font-weight: 750;
  color: #22788e;
}

.weather-amount span {
  font-size: 11px;
  font-weight: 500;
  color: #6b98a4;
}

.weather-description {
  font-size: 10px;
  color: #678c98;
  text-align: center;
  margin: 5px 0 8px;
}

.rain-track {
  width: 100%;
  height: 5px;
  border-radius: 8px;
  background: #d2e7ec;
  overflow: hidden;
  margin-top: auto;
}

.rain-track > div {
  height: 100%;
  border-radius: 8px;
  background: linear-gradient(90deg,#90e3ec,#299bbe);
}

/* FIXED HEIGHT SCENE CARDS */

[class*="st-key-scene_box_"] {
  position: relative;
  height: 340px !important;
  min-height: 340px !important;
  max-height: 340px !important;
  padding: 10px 14px 15px !important;
  margin-bottom: 18px;
  background: rgba(247,253,255,.95);
  border: 2px solid #cde8ef;
  border-radius: 23px;
  box-shadow: 0 8px 25px #1a608811;
  overflow: hidden;
}

[class*="st-key-scene_box_"][class*="_on"] {
  border-color: #2da4af;
  background: rgba(230,249,247,.97);
}

[class*="st-key-scene_button_"] button {
  position: relative !important;
  width: 100% !important;
  height: 170px !important;
  min-height: 170px !important;
  background: transparent !important;
  border: none !important;
  border-radius: 17px !important;
  display: flex !important;
  align-items: flex-end !important;
  justify-content: center !important;
  padding-bottom: 12px !important;
  color: #28586a !important;
  font-size: 17px !important;
  font-weight: 650 !important;
  overflow: hidden !important;
  cursor: pointer !important;
}

[class*="st-key-scene_button_"] button::before {
  position: absolute;
  top: 18px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 66px;
  pointer-events: none;
}

[class*="st-key-scene_button_bathroom"] button::before { content:"🚽"; }
[class*="st-key-scene_button_kitchen"] button::before { content:"🚰"; }
[class*="st-key-scene_button_laundry"] button::before { content:"🧺"; }
[class*="st-key-scene_button_garden"] button::before { content:"🌿"; }
[class*="st-key-scene_button_driveway"] button::before { content:"🚙"; }
[class*="st-key-scene_button_living"] button::before { content:"🛋️"; }

[class*="st-key-scene_box_"][class*="_on"]::after {
  content: "✓";
  position: absolute;
  top: 13px;
  right: 14px;
  z-index: 4;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #2b9faa;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

[class*="st-key-scene_button_"] button::after {
  display: none;
  position: absolute;
  font-size: 24px;
  pointer-events: none;
}

[class*="st-key-scene_button_bathroom_on"] button::after,
[class*="st-key-scene_button_kitchen_on"] button::after {
  content: "💧";
  display: block;
  top: 43px;
  left: 23%;
  animation: sceneDrop 2s infinite;
}

[class*="st-key-scene_button_laundry_on"] button::after {
  content: "🫧";
  display: block;
  top: 53px;
  right: 17%;
  animation: sceneBubble 2.8s infinite;
}

[class*="st-key-scene_button_garden_on"] button::after,
[class*="st-key-scene_button_driveway_on"] button::after {
  content: "💦";
  display: block;
  top: 45px;
  right: 17%;
  animation: sceneSpray 2.5s infinite;
}

[class*="st-key-scene_button_living_on"] button::after {
  content: "🌱";
  display: block;
  top: 47px;
  right: 17%;
  animation: sceneSway 3s infinite;
}

@keyframes sceneDrop {
  0% { transform:translateY(-9px);opacity:0; }
  50% { opacity:1; }
  100% { transform:translateY(18px);opacity:0; }
}

@keyframes sceneBubble {
  0% { transform:translateY(13px);opacity:0; }
  50% { opacity:1; }
  100% { transform:translateY(-16px);opacity:0; }
}

@keyframes sceneSpray {
  50% { transform:translateX(13px);opacity:.5; }
}

@keyframes sceneSway {
  50% { transform:rotate(12deg); }
}

[class*="st-key-scene_controls_"] {
  height: 120px !important;
  min-height: 120px !important;
  max-height: 120px !important;
  padding: 8px 8px 0 !important;
  border-top: 1px solid #83b9c344;
  overflow: hidden;
}

.scene-reserved {
  height: 100px;
}

.scene-amount {
  margin-top: 7px;
  text-align: center;
  color: #227f91;
  font-size: 19px;
  font-weight: 750;
}

.scene-amount span {
  font-size: 12px;
  color: #698f99;
  font-weight: 500;
}

/* Responsive */

@media (max-width: 1100px) {
  .weather-grid {
    grid-template-columns: repeat(4, minmax(0,1fr));
  }
}

@media (max-width: 700px) {
  .weather-grid {
    grid-template-columns: repeat(2, minmax(0,1fr));
  }

  [class*="st-key-location_option_"] button {
    height: 120px !important;
    font-size: 13px !important;
  }

  [class*="st-key-scene_button_"] button::before {
    font-size: 45px;
  }

  [class*="st-key-panel_"] {
    padding: 14px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .cloud, .rain-drop,
  [class*="st-key-scene_button_"] button::after {
    animation: none !important;
  }
}
"""

# CSS can be rendered directly as HTML.
# Unlike complex card HTML, this is only a style element.
st.html("<style>" + MAIN_CSS + "</style>")


# ============================================================
# WEATHER ANIMATED CARD HTML
# ============================================================

def render_weather_cards(dates, rainfall, fetched_at):
    entries = list(zip(dates, rainfall))[:7]

    if not entries:
        st.info("No rainfall forecast available.")
        return

    values = [
        max(0.0, float(amount))
        for _, amount in entries
    ]

    total = sum(values)
    maximum = max(values)

    best_index = values.index(maximum)

    if total > 0:
        best_day = date_label(entries[best_index][0])
    else:
        best_day = "No rain forecast"

    st.markdown("#### 🌦️ Seven-Day Rainfall Outlook")

    col1, col2, col3 = st.columns(3)

    col1.metric("Expected Rainfall", f"{total:.1f} mm")
    col2.metric("Highest Rainfall Day", best_day)
    col3.metric("Peak Daily Rainfall", f"{maximum:.1f} mm")

    cards = []

    for date, raw_rain in entries:
        amount = max(0.0, float(raw_rain))
        category, description = rain_category(amount)

        percentage = (
            amount / maximum * 100
            if maximum > 0
            else 0
        )

        drops = "".join(
            f'<span class="rain-drop rain-drop-{i}"></span>'
            for i in range(6)
        )

        # IMPORTANT:
        # No Markdown parser is used for this HTML.
        cards.append(
            f"""
            <div class="weather-card {category}">
                <div class="weather-date">
                    {html.escape(date_label(date))}
                </div>
                <div class="weather-visual">
                    <div class="cloud"></div>
                    <div class="rain-drops">{drops}</div>
                </div>
                <div class="weather-amount">
                    {amount:g}<span> mm</span>
                </div>
                <div class="weather-description">
                    {html.escape(description)}
                </div>
                <div class="rain-track">
                    <div style="width:{percentage:.1f}%"></div>
                </div>
            </div>
            """
        )

    weather_html = (
        '<div class="weather-grid">'
        + "".join(cards)
        + "</div>"
    )

    # FIX: st.html renders the entire HTML structure.
    # It prevents the raw rain-drop tags appearing as text.
    st.html(weather_html)

    try:
        retrieved = datetime.fromisoformat(
            fetched_at
        ).strftime("%d %b %Y · %H:%M %Z").strip()
    except ValueError:
        retrieved = fetched_at

    st.caption(
        f"Data retrieved: {retrieved}. "
        "Rain animations reflect forecast precipitation "
        "amounts, not independently reported weather types."
    )


# ============================================================
# HEADER
# ============================================================

left, right = st.columns(
    [5, 1],
    vertical_alignment="center",
)

with left:
    st.title("💧 Rainwater Smart Planner")
    st.caption("Smart Rainwater Collection & Allocation")

with right:
    st.button(
        "Home",
        on_click=return_home,
        use_container_width=True,
    )


# ============================================================
# RESULTS VIEW
# ============================================================

show_results = (
    st.session_state.show_results
    and st.session_state.plan is not None
)

if show_results:
    if st.button(
        "← Back to Settings",
        key="back_to_settings",
    ):
        st.session_state.show_results = False
        st.rerun()

    saved = st.session_state.plan
    comparison = saved["comparison"]
    baseline = comparison["baseline"]
    optimized = comparison["optimized"]
    dates = saved["dates"]

    with st.container(key="panel_results"):
        st.subheader("04 · Allocation Dashboard")

        params = saved["params"]

        st.caption(
            f"Location: {saved['location']} | "
            "Weather data: Open-Meteo"
        )

        demands_text = " · ".join(
            f"{name} {amount:g} L"
            for name, amount in params["demands"].items()
        )

        st.caption(
            f"Parameters: area {params['area']:g} m² · "
            f"tank {params['capacity']:g} L · "
            f"efficiency {params['efficiency']:.0%} · "
            f"initial {params['initial_storage']} L · "
            f"reserve {params['reserve']} L"
        )

        st.caption(f"Demand: {demands_text}")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Collected",
            f"{optimized['total_collected']:,.0f} L",
        )

        c2.metric(
            "Allocated",
            f"{optimized['total_allocated']:,.0f} L",
        )

        c3.metric(
            "Shortage",
            f"{optimized['total_shortage']:,.0f} L",
        )

        c4.metric(
            "Overflow",
            f"{optimized['total_overflow']:,.0f} L",
        )

        st.subheader("05 · Optimization")

        left, right = st.columns(2)

        left.metric(
            "Baseline Overflow",
            f"{baseline['total_overflow']:,.1f} L",
        )

        right.metric(
            "Optimized Overflow",
            f"{optimized['total_overflow']:,.1f} L",
        )

        st.metric(
            "Overflow Reduction",
            f"{comparison['overflow_reduction']:,.1f} L",
        )

        if comparison["schedule_changed"]:
            st.success("An optimized schedule was found.")
        else:
            st.info("No schedule changes are required.")

        st.subheader("06 · Seven-Day Water Plan")

        df = make_daily_table(
            optimized,
            dates,
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### Tank Storage")

        st.line_chart(
            df.set_index("Date")[["Remaining (L)"]]
        )

        st.markdown("#### Collection and Allocation")

        st.bar_chart(
            df.set_index("Date")[
                ["Collected (L)", "Allocated (L)"]
            ]
        )

        st.subheader("07 · Smart Recommendations")

        for item in saved["recommendations"]:
            message = (
                f"**{item['title']}**\n\n"
                f"{item['message']}"
            )

            if item["level"] == "success":
                st.success(message)
            elif item["level"] == "warning":
                st.warning(message)
            else:
                st.info(message)

        st.subheader("08 · Export")

        st.download_button(
            "Download Allocation Plan",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="rainwater_plan.csv",
            mime="text/csv",
        )

    st.stop()


# ============================================================
# LOCATION SELECTION
# ============================================================

with st.container(key="panel_location"):
    st.subheader("01 · Your Location")

    st.caption(
        "Select a location to explore local rainfall "
        "forecasts and generate your water allocation plan."
    )

    mode = st.session_state.location_mode

    location_left, location_right = st.columns(
        2,
        gap="medium",
    )

    with location_left:
        selected = "active" if mode == "gps" else "inactive"

        with st.container(
            key=f"location_option_gps_{selected}"
        ):
            st.button(
                "Use My Location",
                key="location_gps",
                use_container_width=True,
                on_click=change_location_mode,
                args=("gps",),
            )

    with location_right:
        selected = "active" if mode == "city" else "inactive"

        with st.container(
            key=f"location_option_city_{selected}"
        ):
            st.button(
                "Search City",
                key="location_city",
                use_container_width=True,
                on_click=change_location_mode,
                args=("city",),
            )

    with st.container(key="panel_location_input"):
        if st.session_state.location_mode == "gps":
            st.markdown("#### 📍 Current Location")

            st.caption(
                "Location access is requested only after "
                "you click the button."
            )

            if st.button("Detect My Location"):
                st.session_state.request_location = True

            if st.session_state.request_location:
                position = get_geolocation()

                if isinstance(position, dict):
                    coords = position.get("coords")

                    if coords:
                        location = {
                            "name": "Current Location",
                            "latitude": float(coords["latitude"]),
                            "longitude": float(coords["longitude"]),
                        }

                        set_location(location)

                if st.session_state.selected_location is None:
                    st.info(
                        "Please allow browser location access."
                    )

        else:
            st.markdown("#### 🌍 Search Worldwide")

            with st.form("search_form"):
                city_input = st.text_input(
                    "City or Region",
                    placeholder="Tokyo, Hong Kong, London...",
                )

                submitted_search = st.form_submit_button(
                    "Search Location",
                    type="primary",
                    use_container_width=True,
                )

            if submitted_search:
                if not city_input.strip():
                    st.warning("Please enter a city name.")
                else:
                    try:
                        st.session_state.city_results = (
                            search_city(city_input.strip())
                        )

                        st.session_state.searched_city = (
                            city_input.strip()
                        )

                    except Exception as exc:
                        st.error(f"Search failed: {exc}")
                        st.session_state.city_results = []

            results = st.session_state.city_results

            if (
                results
                and city_input.strip()
                == st.session_state.searched_city
            ):
                options = {}

                for item in results:
                    label = (
                        f"{item['name']}, "
                        f"{item.get('admin1', '')}, "
                        f"{item.get('country', '')} "
                        f"(ID: {item['id']})"
                    )
                    options[label] = item

                label = st.selectbox(
                    "Choose a Matching Location",
                    list(options.keys()),
                )

                selected_location = options[label]
                set_location(selected_location)

            elif submitted_search and not results:
                st.info("No matching cities were found.")

    location = st.session_state.selected_location

    if location is not None:
        lat = float(location["latitude"])
        lon = float(location["longitude"])

        # FIX: use st.html for generated HTML.
        st.html(
            f"""
            <div class="location-confirmation">
                <div class="location-name">
                    ✓ {html.escape(str(location['name']))}
                </div>
                <div class="location-coordinates">
                    Latitude: {lat:.4f}°
                    &nbsp; · &nbsp;
                    Longitude: {lon:.4f}°
                </div>
            </div>
            """
        )

        try:
            dates, rainfall, fetched_at = load_weather(
                lat,
                lon,
            )

            if len(dates) != len(rainfall):
                raise ValueError(
                    "The returned forecast data lengths do not match."
                )

            render_weather_cards(
                dates,
                rainfall,
                fetched_at,
            )

        except Exception as exc:
            st.warning(
                f"Rainfall preview unavailable: {exc}"
            )


# ============================================================
# SYSTEM SCHEMATIC COMPONENT
# ============================================================

SCHEMATIC_HTML = """
<svg id="schematic" viewBox="0 0 500 430" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Rainwater system schematic">
  <defs>
    <linearGradient id="rooffill" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#d2e4ea"></stop>
      <stop offset="50%" stop-color="#a4c2cf"></stop>
      <stop offset="100%" stop-color="#7fa5b7"></stop>
    </linearGradient>
    <linearGradient id="waterfill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="rgba(96,186,220,0.5)"></stop>
      <stop offset="100%" stop-color="rgba(32,132,178,0.72)"></stop>
    </linearGradient>
    <linearGradient id="surfacefill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="rgba(198,239,248,0.95)"></stop>
      <stop offset="100%" stop-color="rgba(126,206,230,0.9)"></stop>
    </linearGradient>
    <pattern id="rivets" width="26" height="20" patternUnits="userSpaceOnUse">
      <circle cx="13" cy="10" r="1.4" fill="rgba(255,255,255,0.55)"></circle>
    </pattern>
    <pattern id="hatch" width="7" height="7" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
      <rect width="7" height="7" fill="rgba(190,60,70,0.05)"></rect>
      <line x1="0" y1="0" x2="0" y2="7" stroke="rgba(190,60,70,0.32)" stroke-width="1.6"></line>
    </pattern>
    <clipPath id="tankclip">
      <path d="M 221 228 L 379 228 L 379 390 A 79 16 0 0 1 221 390 Z"></path>
    </clipPath>
  </defs>

  <ellipse cx="300" cy="406" rx="88" ry="9" fill="rgba(25,78,90,0.07)"></ellipse>

  <g id="rain" fill="#7cc3e0">
    <ellipse class="drop" style="animation-delay:0s" cx="150" cy="40" rx="2.2" ry="4.2"></ellipse>
    <ellipse class="drop" style="animation-delay:-.5s" cx="190" cy="30" rx="2.2" ry="4.2"></ellipse>
    <ellipse class="drop" style="animation-delay:-1.1s" cx="230" cy="44" rx="2.2" ry="4.2"></ellipse>
    <ellipse class="drop" style="animation-delay:-.3s" cx="270" cy="28" rx="2.2" ry="4.2"></ellipse>
    <ellipse class="drop" style="animation-delay:-.8s" cx="310" cy="42" rx="2.2" ry="4.2"></ellipse>
    <ellipse class="drop" style="animation-delay:-1.4s" cx="345" cy="32" rx="2.2" ry="4.2"></ellipse>
  </g>

  <polygon id="roofside" points="60,150 210,130 210,139 60,159" fill="#5d8799"></polygon>
  <polygon id="roof" points="60,150 88,92 238,72 210,130" fill="url(#rooffill)" stroke="#6d96ab" stroke-width="1.8" stroke-linejoin="round"></polygon>
  <polygon id="roofdots" points="60,150 88,92 238,72 210,130" fill="url(#rivets)" pointer-events="none"></polygon>
  <polyline id="roofedge" points="88,92 238,72" fill="none" stroke="rgba(255,255,255,0.6)" stroke-width="2" pointer-events="none"></polyline>
  <text id="arealabel" x="252" y="90" font-size="12.5" font-weight="600">Collection Area (50 m²)</text>

  <path id="loss" d="M 210 214 V 252" fill="none" stroke="#9db4be" stroke-width="2.5" stroke-dasharray="4 6" stroke-linecap="round"></path>
  <path id="pipe" d="M 210 136 V 202 Q 210 212 220 212 L 228 212" fill="none" stroke="#2b9faa" stroke-width="6" stroke-linecap="round"></path>
  <line id="trickle" x1="228" y1="214" x2="228" y2="238" stroke="#2b9faa" stroke-width="4" stroke-dasharray="3 5" stroke-linecap="round" opacity="0.75"></line>
  <text id="collectedlabel" x="200" y="188" font-size="12.5" font-weight="600" text-anchor="end">80% collected</text>
  <text id="losslabel" x="200" y="208" font-size="11.5" text-anchor="end">20% loss</text>

  <rect x="225" y="245" width="150" height="145" fill="rgba(255,255,255,0.3)"></rect>
  <ellipse cx="300" cy="390" rx="75" ry="13" fill="rgba(255,255,255,0.3)"></ellipse>

  <g clip-path="url(#tankclip)">
    <rect id="water" x="221" y="390" width="158" height="16" fill="url(#waterfill)" style="display:none"></rect>
    <rect id="reservezone" x="221" y="390" width="158" height="0" fill="url(#hatch)"></rect>
    <ellipse id="watersurface" cx="300" cy="390" rx="75" ry="13" fill="url(#surfacefill)" style="display:none"></ellipse>
  </g>

  <rect x="237" y="256" width="13" height="122" rx="6.5" fill="rgba(255,255,255,0.45)" pointer-events="none"></rect>

  <ellipse cx="300" cy="245" rx="75" ry="13" fill="rgba(246,252,253,0.55)" stroke="#2f6475" stroke-width="2"></ellipse>
  <line x1="225" y1="245" x2="225" y2="390" stroke="#2f6475" stroke-width="2"></line>
  <line x1="375" y1="245" x2="375" y2="390" stroke="#2f6475" stroke-width="2"></line>
  <path d="M 225 390 A 75 13 0 0 0 375 390" fill="none" stroke="#2f6475" stroke-width="2"></path>

  <ellipse id="reserveline" cx="300" cy="390" rx="75" ry="13" fill="none" stroke="#c2454f" stroke-width="1.8" stroke-dasharray="6 5" style="display:none"></ellipse>

  <text id="initiallabel" x="384" y="394" font-size="11.5" font-weight="600" style="display:none">Initial Storage</text>
  <text id="reservelabel" x="384" y="394" font-size="11.5" font-weight="600" style="display:none">Minimum Reserve</text>

  <rect id="dragzone" x="221" y="230" width="158" height="175" fill="transparent" style="cursor: ns-resize;"></rect>
  <text id="draghint" x="300" y="322" font-size="11" fill="rgba(25,78,90,0.38)" text-anchor="middle" pointer-events="none">drag water level</text>
</svg>
"""

SCHEMATIC_CSS = """
:host { display: block; }
#schematic {
  width: 100%;
  height: 100%;
  display: block;
  background: linear-gradient(180deg, #ffffff, #f2fafb);
  border: 1px solid #ddeef2;
  border-radius: 18px;
}
#schematic text { font-family: inherit; fill: #194e5a; }
#collectedlabel { fill: #2b9faa; }
#losslabel { fill: #7e97a2; }
#initiallabel { fill: #22788e; }
#reservelabel { fill: #d32f2f; }
.drop { animation: schematicRain 1.9s linear infinite; }
@keyframes schematicRain {
  0% { transform: translateY(-8px); opacity: 0; }
  30% { opacity: .95; }
  100% { transform: translateY(30px); opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .drop { animation: none; }
}
"""

SCHEMATIC_JS = """
export default function({parentElement, data, setTriggerValue}) {
  const svg = parentElement.querySelector("#schematic");
  if (!svg) return;
  const $ = (id) => parentElement.querySelector("#" + id);

  const RIMY = 245, BOTY = 390, FLOORY = 406;
  const H = BOTY - RIMY;
  const TANK_LEFT = 225;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  function render(d) {
    const area = clamp(Number(d.area) || 50, 1, 10000);
    const cap = Math.max(1, Number(d.capacity) || 500);
    const eff = clamp(Number(d.efficiency) || 0, 0, 1);
    const init = clamp(Number(d.initial) || 0, 0, cap);
    const reserve = clamp(Number(d.reserve) || 0, 0, cap);

    // roof panel scales with collection area
    const W = clamp(150 + (area - 1) / 149 * 80, 150, 230);
    const face = `60,150 88,92 ${88 + W},72 ${60 + W},130`;
    $("roof").setAttribute("points", face);
    $("roofdots").setAttribute("points", face);
    $("roofside").setAttribute(
      "points",
      `60,150 ${60 + W},130 ${60 + W},139 60,159`
    );
    $("roofedge").setAttribute("points", `88,92 ${88 + W},72`);

    const areaLabel = $("arealabel");
    areaLabel.setAttribute("x", String(88 + W + 14));
    areaLabel.textContent = `Collection Area (${Math.round(area)} m²)`;

    // downpipe from roof corner, splitting into collected / loss
    const xp = 60 + W;
    const endX = TANK_LEFT + 3;
    let pipePath;
    if (Math.abs(endX - xp) < 14) {
      pipePath = `M ${xp} 136 V 212 L ${endX} 212`;
    } else {
      const dir = endX > xp ? 1 : -1;
      pipePath =
        `M ${xp} 136 V 202 Q ${xp} 212 ${xp + dir * 10} 212 L ${endX} 212`;
    }
    const pipe = $("pipe");
    pipe.setAttribute("d", pipePath);
    pipe.setAttribute("stroke-width", (2.5 + eff * 5).toFixed(1));
    pipe.setAttribute("stroke-opacity", (0.45 + eff * 0.55).toFixed(2));

    $("trickle").setAttribute(
      "stroke-opacity",
      (0.25 + eff * 0.6).toFixed(2)
    );

    const loss = $("loss");
    loss.setAttribute("d", `M ${xp} 214 V 252`);
    loss.setAttribute(
      "stroke-opacity",
      (0.15 + (1 - eff) * 0.85).toFixed(2)
    );

    const collected = $("collectedlabel");
    collected.textContent = `${Math.round(eff * 100)}% collected`;
    collected.setAttribute("x", String(xp - 12));

    const lossLabel = $("losslabel");
    lossLabel.textContent = `${Math.round((1 - eff) * 100)}% loss`;
    lossLabel.setAttribute("x", String(xp - 12));

    setWater(init, reserve, cap);
  }

  function setWater(init, reserve, cap) {
    const wy = BOTY - clamp(init / cap, 0, 1) * H;
    const showWater = init > 0;
    const water = $("water");
    water.setAttribute("y", String(wy));
    water.setAttribute("height", String(FLOORY - wy));
    water.style.display = showWater ? "" : "none";
    const surface = $("watersurface");
    surface.setAttribute("cy", String(wy));
    surface.style.display = showWater ? "" : "none";

    const rh = clamp(reserve / cap, 0, 1) * H;
    const ry = BOTY - rh;
    const showReserve = reserve > 0;
    const zone = $("reservezone");
    zone.setAttribute("y", String(ry));
    zone.setAttribute("height", String(FLOORY - ry));
    zone.style.display = showReserve ? "" : "none";
    const line = $("reserveline");
    line.setAttribute("cy", String(ry));
    line.style.display = showReserve ? "" : "none";

    // keep the two side labels from overlapping each other
    const initialLabel = $("initiallabel");
    const reserveLabel = $("reservelabel");
    let yi = clamp(wy + 4, RIMY + 13, BOTY - 2);
    let yr = clamp(ry + 4, RIMY + 13, BOTY - 2);
    if (showWater && showReserve && Math.abs(yi - yr) < 14) {
      if (wy <= ry) yr = Math.min(yi + 14, BOTY + 2);
      else yi = Math.min(yr + 14, BOTY + 2);
    }
    initialLabel.setAttribute("y", String(yi));
    initialLabel.style.display = showWater ? "" : "none";
    reserveLabel.setAttribute("y", String(yr));
    reserveLabel.style.display = showReserve ? "" : "none";
  }

  render(data || {});

  const zone = $("dragzone");
  const cap0 = Math.max(1, Number((data || {}).capacity) || 500);
  const reserve0 = clamp(Number((data || {}).reserve) || 0, 0, cap0);
  let dragging = false;

  function litersFromEvent(e) {
    const rect = svg.getBoundingClientRect();
    const y = (e.clientY - rect.top) * (430 / rect.height);
    return clamp((BOTY - y) / H, 0, 1) * cap0;
  }

  zone.addEventListener("pointerdown", (e) => {
    dragging = true;
    zone.setPointerCapture(e.pointerId);
    setWater(litersFromEvent(e), reserve0, cap0);
    e.preventDefault();
  });
  zone.addEventListener("pointermove", (e) => {
    if (dragging) setWater(litersFromEvent(e), reserve0, cap0);
  });
  zone.addEventListener("pointerup", (e) => {
    if (!dragging) return;
    dragging = false;
    setTriggerValue("level", Math.round(litersFromEvent(e)));
  });
}
"""

system_schematic = component(
    "rainwater_system_schematic_v1",
    html=SCHEMATIC_HTML,
    css=SCHEMATIC_CSS,
    js=SCHEMATIC_JS,
)


# ============================================================
# WATER SYSTEM SETTINGS
# ============================================================

# Clamp storage/reserve widget state whenever tank capacity shrinks.
_capacity_state = float(st.session_state.get("ws_capacity", 500.0))
for _state_key in ("ws_init", "ws_reserve"):
    if _state_key in st.session_state:
        st.session_state[_state_key] = max(
            0, min(int(st.session_state[_state_key]), int(_capacity_state))
        )

with st.container(key="panel_settings"):
    st.subheader("02 · Water System Settings")

    st.caption(
        "Drag the water level in the schematic or tune the controls. "
        "Water demand values are selected on the cards below."
    )

    schem_col, ctrl_col = st.columns([11, 10], gap="large")

    with schem_col:
        schematic_result = system_schematic(
            key="system_schematic",
            data={
                "area": float(st.session_state.get("ws_area", 50.0)),
                "capacity": float(st.session_state.get("ws_capacity", 500.0)),
                "efficiency": float(st.session_state.get("ws_eff", 0.8)),
                "initial": float(st.session_state.get("ws_init", 0)),
                "reserve": float(st.session_state.get("ws_reserve", 0)),
            },
            height=440,
            on_level_change=lambda: None,
        )

        _area_now = float(st.session_state.get("ws_area", 50.0))
        _cap_now = float(st.session_state.get("ws_capacity", 500.0))
        _eff_now = float(st.session_state.get("ws_eff", 0.8))
        _init_now = float(st.session_state.get("ws_init", 0))
        _res_now = float(st.session_state.get("ws_reserve", 0))

        _per_10mm = _area_now * 10.0 * _eff_now
        _tank_pct = (_per_10mm / _cap_now * 100.0) if _cap_now else 0.0
        _usable = max(0.0, _init_now - _res_now)

        st.html(
            """
            <style>
            .kpi-pills {
              display: flex;
              gap: 10px;
              flex-wrap: wrap;
              margin-top: 10px;
              font-family: inherit;
            }
            .kpi-pill {
              padding: 9px 16px;
              background: #ffffff;
              border: 1px solid #cfe6ec;
              border-radius: 999px;
              font-size: 13px;
              color: #57808d;
            }
            .kpi-pill strong { color: #194e5a; }
            .kpi-pill.kpi-accent {
              border-color: #2b9faa;
              box-shadow: 0 0 0 1px #2b9faa33;
            }
            </style>
            <div class="kpi-pills">
              <div class="kpi-pill kpi-accent">
                Per 10mm rain:
                <strong>"""
            f"{_per_10mm:,.0f} L"
            "</strong> ("
            f"{_tank_pct:.0f}% of tank"
            """)</div>
              <div class="kpi-pill">
                Usable Water:
                <strong>"""
            f"{_usable:,.0f} L"
            """</strong></div>
            </div>
            """
        )

    with ctrl_col:
        dragged_level = schematic_result.get("level")
        if dragged_level is not None:
            st.session_state.ws_init = int(
                max(0.0, min(_capacity_state, float(dragged_level)))
            )
            invalidate_plan()
            st.rerun()

        area = st.number_input(
            "Collection Area (m²)",
            min_value=1.0,
            max_value=10000.0,
            value=50.0,
            step=5.0,
            key="ws_area",
            on_change=invalidate_plan,
        )
        st.caption(f"≈ {area / 50.0:.1f} × a small detached-house roof")

        capacity = st.number_input(
            "Tank Capacity (L)",
            min_value=10.0,
            max_value=100000.0,
            value=500.0,
            step=100.0,
            key="ws_capacity",
            on_change=invalidate_plan,
        )
        st.caption(f"≈ {capacity / 200.0:.1f} bathtubs")

        st.markdown("**Collection Efficiency**")

        _eff_current = float(st.session_state.get("ws_eff", 0.8))

        preset1, preset2, preset3 = st.columns(3)
        preset1.button(
            "Metal/Tile 0.90",
            use_container_width=True,
            type=(
                "primary"
                if abs(_eff_current - 0.9) < 1e-9
                else "secondary"
            ),
            on_click=set_efficiency_preset,
            args=(0.9,),
        )
        preset2.button(
            "Concrete 0.80",
            use_container_width=True,
            type=(
                "primary"
                if abs(_eff_current - 0.8) < 1e-9
                else "secondary"
            ),
            on_click=set_efficiency_preset,
            args=(0.8,),
        )
        preset3.button(
            "Green roof 0.60",
            use_container_width=True,
            type=(
                "primary"
                if abs(_eff_current - 0.6) < 1e-9
                else "secondary"
            ),
            on_click=set_efficiency_preset,
            args=(0.6,),
        )

        efficiency = st.slider(
            "Collection Efficiency",
            min_value=0.0,
            max_value=1.0,
            value=0.8,
            step=0.05,
            key="ws_eff",
            label_visibility="collapsed",
            on_change=invalidate_plan,
        )

        initial_storage = st.number_input(
            "Initial Storage (L)",
            min_value=0,
            max_value=100000,
            value=0,
            step=1,
            key="ws_init",
            on_change=invalidate_plan,
        )

        reserve = st.number_input(
            "Minimum Reserve (L)",
            min_value=0,
            max_value=100000,
            value=0,
            step=1,
            key="ws_reserve",
            on_change=invalidate_plan,
        )


# ============================================================
# HOUSEHOLD WATER USAGE
# ============================================================

st.subheader("03 · Household Water Usage")

st.caption(
    "Select a scene and set Low, Medium, "
    "or High water demand."
)

scene_names = list(SCENES.keys())

for start in range(0, len(scene_names), 3):
    columns = st.columns(3, gap="medium")

    for column, name in zip(
        columns,
        scene_names[start:start + 3],
    ):
        slug, icon, base, priority, flexible, unit = SCENES[name]

        chosen = name in st.session_state.selected_scenes
        state = "on" if chosen else "off"

        with column:
            with st.container(
                height=CARD_HEIGHT,
                border=False,
                key=f"scene_box_{slug}_{state}",
            ):
                with st.container(
                    key=f"scene_button_{slug}_{state}"
                ):
                    st.button(
                        name,
                        key=f"toggle_{slug}",
                        use_container_width=True,
                        on_click=toggle_scene,
                        args=(name,),
                    )

                with st.container(
                    key=f"scene_controls_{slug}"
                ):
                    if chosen:
                        st.select_slider(
                            f"{name} Usage",
                            options=["Low", "Medium", "High"],
                            key=f"level_{slug}",
                            label_visibility="collapsed",
                            on_change=change_level,
                            args=(name, slug),
                        )

                        demand = demand_for(name)

                        st.html(
                            f"""
                            <div class="scene-amount">
                                {demand:g} L
                                <span>/ {unit}</span>
                            </div>
                            """
                        )
                    else:
                        st.html(
                            '<div class="scene-reserved"></div>'
                        )


selected = list(st.session_state.selected_scenes)


# ============================================================
# GENERATE PLAN
# ============================================================

submitted = st.button(
    "Generate Smart Plan",
    type="primary",
    use_container_width=True,
)

if submitted:
    invalidate_plan()

    location = st.session_state.selected_location

    if location is None:
        st.warning("Please select a location.")

    elif not selected:
        st.warning("Please select a water-use scene.")

    elif initial_storage > capacity:
        st.error(
            "Initial Storage cannot exceed Tank Capacity. "
            "Please lower the initial storage or raise the capacity."
        )

    elif reserve > capacity:
        st.error(
            "Minimum Reserve cannot exceed Tank Capacity. "
            "Please lower the reserve or raise the capacity."
        )

    else:
        with st.spinner("Generating allocation plan..."):
            try:
                dates, rainfall, _ = load_weather(
                    float(location["latitude"]),
                    float(location["longitude"]),
                )

                tasks = build_tasks(
                    selected,
                    len(dates),
                )

                comparison = compare_strategies(
                    rainfall=rainfall,
                    area=area,
                    capacity=capacity,
                    tasks=tasks,
                    efficiency=efficiency,
                    initial_storage=int(initial_storage),
                    reserve=int(reserve),
                )

                recommendations = generate_recommendations(
                    comparison,
                    dates,
                    tasks,
                )

                st.session_state.plan = {
                    "comparison": comparison,
                    "recommendations": recommendations,
                    "dates": dates,
                    "location": location["name"],
                    "params": {
                        "area": area,
                        "capacity": capacity,
                        "efficiency": efficiency,
                        "initial_storage": int(initial_storage),
                        "reserve": int(reserve),
                        "demands": {
                            name: demand_for(name)
                            for name in selected
                        },
                    },
                }

            except Exception as exc:
                st.error(
                    f"Calculation failed: {exc}"
                )
            else:
                st.session_state.show_results = True
                st.rerun()


st.caption(
    "Weather animations indicate forecast rainfall intensity. "
    "Background water level represents the number of selected "
    "scenes, not the actual volume of stored rainwater. "
    "Demand estimates are illustrative."
)
