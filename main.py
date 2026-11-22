
import pandas as pd
import streamlit as st
from streamlit_js_eval import get_geolocation

from rainfall_service import search_city, get_rainfall_forecast
from rainwater_engine import WaterTask, compare_strategies
from recommendation_engine import generate_recommendations


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Rainwater Smart Planner",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SCENES = {
    "Bathroom": {
        "slug": "bathroom",
        "icon": "🚽",
        "base": 60.0,
        "priority": 1,
        "flexible": False,
        "unit": "day",
    },
    "Kitchen": {
        "slug": "kitchen",
        "icon": "🚰",
        "base": 15.0,
        "priority": 2,
        "flexible": False,
        "unit": "day",
    },
    "Laundry": {
        "slug": "laundry",
        "icon": "🧺",
        "base": 80.0,
        "priority": 3,
        "flexible": True,
        "unit": "use",
    },
    "Garden": {
        "slug": "garden",
        "icon": "🌿",
        "base": 40.0,
        "priority": 2,
        "flexible": False,
        "unit": "day",
    },
    "Driveway": {
        "slug": "driveway",
        "icon": "🚙",
        "base": 100.0,
        "priority": 4,
        "flexible": True,
        "unit": "use",
    },
    "Living Room": {
        "slug": "living",
        "icon": "🛋️",
        "base": 20.0,
        "priority": 3,
        "flexible": False,
        "unit": "day",
    },
}

LEVELS = {
    "Low": 0.6,
    "Medium": 1.0,
    "High": 1.5,
}

st.session_state.setdefault("entered", False)
st.session_state.setdefault(
    "selected_scenes", ["Bathroom", "Garden"]
)
st.session_state.setdefault("plan", None)
st.session_state.setdefault("request_location", False)

for name, config in SCENES.items():
    st.session_state.setdefault(
        f"level_{config['slug']}", "Medium"
    )


# ============================================================
# HELPERS
# ============================================================

def enter_application():
    st.session_state.entered = True


def return_home():
    st.session_state.entered = False


def invalidate_plan():
    st.session_state.plan = None


def toggle_scene(name):
    selected = list(st.session_state.selected_scenes)

    if name in selected:
        selected.remove(name)
    else:
        selected.append(name)

    st.session_state.selected_scenes = selected
    invalidate_plan()


def scene_demand(name):
    config = SCENES[name]
    level = st.session_state[f"level_{config['slug']}"]
    return round(config["base"] * LEVELS[level], 2)


def build_tasks(selected, days):
    tasks = []

    for name in selected:
        config = SCENES[name]
        amount = scene_demand(name)

        if config["flexible"]:
            tasks.append(
                WaterTask(
                    name=name,
                    amount=amount,
                    priority=config["priority"],
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
                        priority=config["priority"],
                        flexible=False,
                        earliest_day=day,
                        latest_day=day,
                    )
                )

    return tasks


def make_daily_table(result, dates):
    rows = []

    for record in result["records"]:
        details = {}

        for item in record["allocations"]:
            name = item["task"]
            details[name] = (
                details.get(name, 0) + item["supplied"]
            )

        rows.append({
            "Date": dates[record["day"] - 1],
            "Rainfall (mm)": record["rainfall"],
            "Collected (L)": record["collected"],
            "Allocated (L)": record["allocated"],
            "Shortage (L)": record["shortage"],
            "Overflow (L)": record["overflow"],
            "Remaining (L)": record["remaining"],
            **details,
        })

    return pd.DataFrame(rows).fillna(0)


# ============================================================
# FULLSCREEN TAP WELCOME
# ============================================================

WELCOME_HTML = """
<div id="welcome">
  <div class="welcome-content">
    <div class="brand">◈ &nbsp; RAINWATER SMART PLANNER</div>
    <h1>Make Every<br><em>Drop Count.</em></h1>
    <p>Collect, manage, and use rainwater smarter.</p>

    <svg class="tap" viewBox="0 0 550 340">
      <defs>
        <linearGradient id="metal" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="#f6fcff"/>
          <stop offset=".25" stop-color="#91aab5"/>
          <stop offset=".5" stop-color="#e0ecf1"/>
          <stop offset=".78" stop-color="#5f7887"/>
          <stop offset="1" stop-color="#bdced8"/>
        </linearGradient>
        <linearGradient id="stream" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="#269fcf"/>
          <stop offset=".5" stop-color="#efffff"/>
          <stop offset="1" stop-color="#43bce5"/>
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
      <ellipse cx="425" cy="262" rx="26" ry="7"
               fill="#34515f"/>

      <g id="lever" role="slider" tabindex="0"
         aria-label="Drag faucet handle"
         aria-valuemin="0" aria-valuemax="100"
         aria-valuenow="0">
        <rect x="264" y="65" width="44" height="50"
              rx="12" fill="url(#metal)"/>
        <rect x="247" y="55" width="163" height="28"
              rx="14" fill="url(#metal)"/>
        <rect x="240" y="35" width="195" height="75"
              fill="transparent"/>
      </g>

      <rect id="tap-water" x="421" y="265"
            width="8" height="0" rx="5"
            fill="url(#stream)"/>
    </svg>

    <div class="instruction">
      DRAG THE HANDLE TO THE RIGHT →
    </div>
    <div class="track"><div id="intro-progress"></div></div>
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
  width: 100vw !important;
  height: 100dvh !important;
  z-index: 2147483000 !important;
}
* { box-sizing: border-box; }
#welcome {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100dvh;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 40%, #284e60, transparent 65%),
    linear-gradient(125deg, #081923, #102d3d);
  color: white;
  font-family: Inter, "Segoe UI", sans-serif;
}
.welcome-content {
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
p { color: #a9c5cd; line-height: 1.8; }
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
  filter: drop-shadow(0 0 9px #91f0ff);
}
.instruction {
  margin-top: -12px;
  color: #9bd7dd;
  font-size: 11px;
  letter-spacing: 2px;
}
.track {
  height: 4px;
  width: 210px;
  margin-top: 18px;
  background: #345968;
  border-radius: 10px;
  overflow: hidden;
}
#intro-progress {
  width: 0%;
  height: 100%;
  background: #8be8ef;
}
#intro-water {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
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
@media(prefers-reduced-motion:reduce) {
  .intro-wave { animation: none; }
}
"""

WELCOME_JS = """
export default function({parentElement, setTriggerValue}) {
  const root = parentElement.querySelector("#welcome");
  const lever = parentElement.querySelector("#lever");
  const water = parentElement.querySelector("#intro-water");
  const stream = parentElement.querySelector("#tap-water");
  const bar = parentElement.querySelector("#intro-progress");

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
    timer = setTimeout(() => setTriggerValue("enter", true), 1000);
  }

  function down(e) {
    if (finished) return;
    dragging = true;
    startX = e.clientX;
    startProgress = progress;
    lever.setPointerCapture(e.pointerId);
    e.preventDefault();
  }

  function move(e) {
    if (!dragging || finished) return;
    update(startProgress + (e.clientX - startX) / 155 * 100);
    if (progress >= 99) finish();
  }

  function up() {
    if (!dragging || finished) return;
    dragging = false;
    if (progress >= 90) finish();
    else update(0);
  }

  function key(e) {
    if (e.key === "ArrowRight") {
      e.preventDefault();
      update(progress + 20);
      if (progress >= 100) finish();
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      update(progress - 20);
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
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
    if (timer !== null) clearTimeout(timer);
  };
}
"""


# ============================================================
# INTRO PAGE
# ============================================================

if not st.session_state.entered:
    st.markdown(
        """
        <style>
        html, body { overflow: hidden !important; }
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stSidebar"] {
          display: none !important;
        }
        .block-container {
          padding: 0 !important;
          max-width: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    welcome_component = st.components.v2.component(
        "rainwater_welcome_v3",
        html=WELCOME_HTML,
        css=WELCOME_CSS,
        js=WELCOME_JS,
    )

    welcome_component(
        key="rainwater_welcome",
        on_enter_change=enter_application,
    )
    st.stop()


# ============================================================
# DYNAMIC WATER BACKGROUND
# ============================================================

WATER_HTML = """
<div class="water-background" aria-hidden="true">
  <div class="water-fill">
    <div class="wave back"></div>
    <div class="wave front"></div>
    <div class="water-body"></div>
    <div class="reflection"></div>
    <div class="reflection second"></div>
    <div class="caustics"></div>
  </div>
</div>
"""

WATER_CSS = """
:host {
  position: fixed !important;
  inset: 0 !important;
  z-index: 0 !important;
  width: 100vw !important;
  height: 100dvh !important;
  pointer-events: none !important;
}
.water-background {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100dvh;
  pointer-events: none;
  overflow: hidden;
  background:
    radial-gradient(circle at 12% 10%, #c6eaf0, transparent 46%),
    radial-gradient(circle at 89% 35%, #c5eddb, transparent 42%),
    linear-gradient(150deg, #f1fafd, #e8f6f4);
}
.water-fill {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
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
.wave {
  position: absolute;
  z-index: 3;
  left: -15%;
  width: 130%;
  height: 66px;
  border-radius: 46% 54% 50% 50%;
}
.wave.back {
  top: -27px;
  background: rgba(129,217,236,.75);
  animation: wave 5.8s ease-in-out infinite alternate;
}
.wave.front {
  top: -14px;
  background: rgba(224,252,255,.46);
  animation: wave 4.2s ease-in-out infinite alternate-reverse;
}
@keyframes wave {
  0% { transform: translate(-2%, -5px) rotate(-.3deg); }
  100% { transform: translate(2%, 9px) rotate(.3deg); }
}
.reflection {
  position: absolute;
  z-index: 4;
  top: -20%;
  left: 20%;
  width: 22%;
  height: 160%;
  transform: rotate(19deg);
  filter: blur(25px);
  background: linear-gradient(
    90deg, transparent, #ffffff30, transparent
  );
  animation: shimmer 8s ease-in-out infinite;
}
.reflection.second {
  left: 70%;
  opacity: .5;
  animation-delay: -4s;
}
@keyframes shimmer {
  50% { transform: rotate(19deg) translateX(25px); }
}
.caustics {
  position: absolute;
  inset: 0;
  opacity: .2;
  background: repeating-radial-gradient(
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
@media(prefers-reduced-motion:reduce) {
  .wave, .reflection, .caustics { animation: none; }
  .water-fill { transition: none; }
}
"""

WATER_JS = """
export default function({parentElement, data}) {
  const element = parentElement.querySelector(".water-fill");
  if (!element) return;

  const level = Math.max(
    0, Math.min(100, Number(data?.level ?? 0))
  );

  const oldLevel = Number(
    window.__rainwaterLevel ?? 0
  );

  element.style.height = `${oldLevel}%`;

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      element.style.height = `${level}%`;
      window.__rainwaterLevel = level;
    });
  });
}
"""

water_component = st.components.v2.component(
    "rainwater_background_v3",
    html=WATER_HTML,
    css=WATER_CSS,
    js=WATER_JS,
)

selected_count = len(st.session_state.selected_scenes)

water_component(
    data={"level": selected_count / 6 * 100},
    key="water_background",
    height=0,
)


# ============================================================
# MAIN PAGE CSS
# ============================================================

st.markdown(
    """
<style>
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
  background: transparent !important;
}

[data-testid="stMainBlockContainer"] {
  position: relative;
  z-index: 1;
  max-width: 1220px;
  padding-top: 2rem;
  padding-bottom: 4rem;
}

.stApp h1, .stApp h2, .stApp h3 {
  color: #194e5a;
}

div[data-testid="stMetric"] {
  padding: 15px;
  border-radius: 15px;
  background: rgba(255,255,255,.85);
}

[class*="st-key-panel_"] {
  padding: 20px;
  border-radius: 22px;
  border: 1px solid rgba(255,255,255,.85);
  background: rgba(255,255,255,.86);
  box-shadow: 0 12px 30px #266a8b16;
  backdrop-filter: blur(15px);
  margin-bottom: 18px;
}

/* Scene card container */

[class*="st-key-scene_box_"] {
  border: 2px solid rgba(202,229,235,.9);
  border-radius: 22px;
  padding: 9px 9px 14px;
  margin-bottom: 16px;
  background: rgba(245,253,255,.93);
  box-shadow: 0 6px 18px #236a8b0c;
}

[class*="st-key-scene_box_"][class*="_on"] {
  border-color: #35a6b0;
  background: rgba(231,250,248,.96);
  box-shadow: 0 10px 25px #23899a23;
}

/* Clickable upper part */

[class*="st-key-scene_button_"] button {
  position: relative !important;
  height: 154px !important;
  width: 100% !important;
  border: none !important;
  border-radius: 17px !important;
  background: transparent !important;
  color: #28586a !important;
  font-size: 17px !important;
  font-weight: 650 !important;
  display: flex !important;
  align-items: flex-end !important;
  justify-content: center !important;
  padding-bottom: 9px !important;
  cursor: pointer !important;
  overflow: hidden !important;
  transition: transform .25s ease !important;
}

[class*="st-key-scene_button_"] button:hover {
  transform: translateY(-3px);
}

/* Scene icons */

[class*="st-key-scene_button_"] button::before {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 62px;
  pointer-events: none;
}

[class*="st-key-scene_button_bathroom"] button::before {
  content: "🚽";
}
[class*="st-key-scene_button_kitchen"] button::before {
  content: "🚰";
}
[class*="st-key-scene_button_laundry"] button::before {
  content: "🧺";
}
[class*="st-key-scene_button_garden"] button::before {
  content: "🌿";
}
[class*="st-key-scene_button_driveway"] button::before {
  content: "🚙";
}
[class*="st-key-scene_button_living"] button::before {
  content: "🛋️";
}

/* Selected check mark */

[class*="st-key-scene_box_"][class*="_on"]::after {
  content: "✓";
  position: absolute;
  z-index: 4;
  top: 13px;
  right: 14px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #2a9eaa;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

/* Decorative animation for selected cards */

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
  top: 33px;
  left: 23%;
  animation: dropMove 2s infinite;
}

[class*="st-key-scene_button_laundry_on"] button::after {
  content: "🫧";
  display: block;
  top: 45px;
  right: 17%;
  animation: bubbleMove 2.8s infinite;
}

[class*="st-key-scene_button_garden_on"] button::after,
[class*="st-key-scene_button_driveway_on"] button::after {
  content: "💦";
  display: block;
  top: 35px;
  right: 17%;
  animation: sprayMove 2.5s infinite;
}

[class*="st-key-scene_button_living_on"] button::after {
  content: "🌱";
  display: block;
  top: 38px;
  right: 17%;
  animation: swayMove 3s infinite;
}

@keyframes dropMove {
  0% { transform: translateY(-9px); opacity: 0; }
  50% { opacity: 1; }
  100% { transform: translateY(18px); opacity: 0; }
}

@keyframes bubbleMove {
  0% { transform: translateY(13px); opacity: 0; }
  50% { opacity: 1; }
  100% { transform: translateY(-16px); opacity: 0; }
}

@keyframes sprayMove {
  50% { transform: translateX(13px); opacity: .5; }
}

@keyframes swayMove {
  50% { transform: rotate(12deg); }
}

/* Per-scene slider */

[class*="st-key-scene_box_"] [data-testid="stSlider"] {
  padding: 2px 12px 0;
}

[class*="st-key-scene_box_"] [data-testid="stSlider"] > div {
  gap: 0;
}

[class*="st-key-scene_box_"] [data-testid="stSlider"] p {
  font-size: 12px;
  color: #347b89;
}

[class*="st-key-scene_box_"] [data-testid="stSlider"] label {
  color: #347b89;
}

.scene-amount {
  text-align: center;
  font-size: 18px;
  font-weight: 750;
  color: #217c8f;
  margin: 0;
  padding-bottom: 3px;
}

.scene-unit {
  font-size: 12px;
  color: #698f99;
}

.stButton button,
div[data-testid="stFormSubmitButton"] button {
  border-radius: 12px;
}

@media(prefers-reduced-motion:reduce) {
  [class*="st-key-scene_button_"] button,
  [class*="st-key-scene_button_"] button::after {
    transition: none !important;
    animation: none !important;
  }
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# PAGE HEADER
# ============================================================

left, right = st.columns(
    [5, 1], vertical_alignment="center"
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
# 01 LOCATION
# ============================================================

with st.container(key="panel_location"):

    st.subheader("01 · Your Location")

    method = st.radio(
        "Location Method",
        ["Use My Location", "Search City"],
        horizontal=True,
    )

    location = None

    if method == "Use My Location":

        if st.button("Get My Location"):
            st.session_state.request_location = True

        if st.session_state.request_location:
            position = get_geolocation()

            if isinstance(position, dict):
                coords = position.get("coords")

                if coords:
                    st.session_state.geo_location = {
                        "name": "Current Location",
                        "latitude": float(
                            coords["latitude"]
                        ),
                        "longitude": float(
                            coords["longitude"]
                        ),
                    }

            location = st.session_state.get(
                "geo_location"
            )

            if location:
                st.success("Location received.")
            else:
                st.info("Allow browser location access.")

    else:

        city_name = st.text_input(
            "Search City",
            placeholder="Tokyo, Hong Kong, London",
        )

        if st.button("Search"):

            try:
                st.session_state.city_results = (
                    search_city(city_name)
                )
                st.session_state.searched_city = city_name

            except (ValueError, RuntimeError) as exc:
                st.error(str(exc))
                st.session_state.city_results = []

        results = st.session_state.get(
            "city_results", []
        )

        if city_name != st.session_state.get(
            "searched_city"
        ):
            results = []

        if results:
            options = {
                (
                    f"{item['name']}, "
                    f"{item.get('admin1', '')}, "
                    f"{item.get('country', '')} "
                    f"(ID: {item['id']})"
                ): item
                for item in results
            }

            city_label = st.selectbox(
                "Choose City",
                list(options.keys()),
            )

            location = options[city_label]
            st.success(f"Location: {city_label}")

    if location is not None:
        st.session_state.selected_location = location
    else:
        st.session_state.pop(
            "selected_location", None
        )


# ============================================================
# 02 SCENE CARDS + LEVEL SLIDERS
# ============================================================

st.subheader("02 · Household Water Usage")

st.caption(
    "Select a scene, then choose its water usage level."
)

scene_names = list(SCENES.keys())

for start in range(0, len(scene_names), 3):
    columns = st.columns(3, gap="medium")

    for column, name in zip(
        columns,
        scene_names[start:start + 3],
    ):
        config = SCENES[name]
        slug = config["slug"]

        chosen = name in st.session_state.selected_scenes
        state = "on" if chosen else "off"

        with column:

            with st.container(
                key=f"scene_box_{slug}_{state}",
            ):

                with st.container(
                    key=f"scene_button_{slug}_{state}",
                ):
                    st.button(
                        name,
                        key=f"toggle_{slug}",
                        use_container_width=True,
                        type="secondary",
                        on_click=toggle_scene,
                        args=(name,),
                    )

                if chosen:
                    st.select_slider(
                        f"{name} Usage",
                        options=["Low", "Medium", "High"],
                        key=f"level_{slug}",
                        on_change=invalidate_plan,
                        label_visibility="collapsed",
                    )

                    amount = scene_demand(name)

                    st.markdown(
                        f'<div class="scene-amount">'
                        f'{amount:g} L'
                        f'<span class="scene-unit">'
                        f' / {config["unit"]}'
                        f'</span></div>',
                        unsafe_allow_html=True,
                    )


# ============================================================
# 03 SYSTEM SETTINGS
# ============================================================

with st.container(key="panel_settings"):

    st.subheader("03 · Water System Settings")

    selected = list(st.session_state.selected_scenes)

    st.caption(
        "Water demands are controlled directly "
        "from the scene cards above."
    )

    with st.form("water_form"):

        c1, c2 = st.columns(2)

        with c1:
            area = st.number_input(
                "Collection Area (m²)",
                min_value=1.0,
                value=50.0,
                step=5.0,
            )

        with c2:
            capacity = st.number_input(
                "Tank Capacity (L)",
                min_value=10.0,
                value=500.0,
                step=100.0,
            )

        with st.expander("Advanced Settings"):

            efficiency = st.slider(
                "Collection Efficiency",
                min_value=0.1,
                max_value=1.0,
                value=0.8,
                step=0.05,
            )

            initial_storage = st.number_input(
                "Initial Storage (L)",
                min_value=0,
                max_value=int(capacity),
                value=0,
            )

            reserve = st.number_input(
                "Minimum Reserve (L)",
                min_value=0,
                max_value=int(capacity),
                value=0,
            )

        submitted = st.form_submit_button(
            "Generate Smart Plan",
            type="primary",
            use_container_width=True,
        )


# ============================================================
# 04 GENERATE PLAN
# ============================================================

if submitted:

    st.session_state.plan = None

    location = st.session_state.get(
        "selected_location"
    )

    if location is None:
        st.warning("Please select a location.")

    elif not selected:
        st.warning(
            "Please select at least one water-use scene."
        )

    else:

        with st.spinner(
            "Generating your allocation plan..."
        ):

            try:
                dates, rainfall = get_rainfall_forecast(
                    location["latitude"],
                    location["longitude"],
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
                    initial_storage=initial_storage,
                    reserve=reserve,
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
                }

            except Exception as exc:
                st.error(
                    f"Calculation failed: {exc}"
                )


# ============================================================
# 05 RESULTS
# ============================================================

saved = st.session_state.get("plan")

if saved is not None:

    comparison = saved["comparison"]
    baseline = comparison["baseline"]
    optimized = comparison["optimized"]
    dates = saved["dates"]

    with st.container(key="panel_results"):

        st.subheader("04 · Allocation Dashboard")

        st.caption(
            f"Location: {saved['location']} | "
            "Weather: Open-Meteo"
        )

        a, b, c, d = st.columns(4)

        a.metric(
            "Collected",
            f"{optimized['total_collected']:,.0f} L",
        )

        b.metric(
            "Allocated",
            f"{optimized['total_allocated']:,.0f} L",
        )

        c.metric(
            "Shortage",
            f"{optimized['total_shortage']:,.0f} L",
        )

        d.metric(
            "Overflow",
            f"{optimized['total_overflow']:,.0f} L",
        )

        st.subheader("05 · Optimization")

        left, right = st.columns(2)

        with left:
            st.metric(
                "Baseline Overflow",
                f"{baseline['total_overflow']:,.1f} L",
            )

        with right:
            st.metric(
                "Optimized Overflow",
                f"{optimized['total_overflow']:,.1f} L",
            )

        st.metric(
            "Overflow Reduction",
            f"{comparison['overflow_reduction']:,.1f} L",
        )

        if comparison["schedule_changed"]:
            st.success(
                "An optimized schedule was found."
            )
        else:
            st.info(
                "No schedule changes are required."
            )

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
            df.set_index("Date")[
                ["Remaining (L)"]
            ]
        )

        st.markdown("#### Collection and Allocation")

        st.bar_chart(
            df.set_index("Date")[
                ["Collected (L)", "Allocated (L)"]
            ]
        )

        st.subheader("07 · Smart Recommendations")

        for item in saved["recommendations"]:

            content = (
                f"**{item['title']}**\n\n"
                f"{item['message']}"
            )

            if item["level"] == "success":
                st.success(content)

            elif item["level"] == "warning":
                st.warning(content)

            else:
                st.info(content)

        st.subheader("08 · Export")

        st.download_button(
            "Download Allocation Plan",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="rainwater_plan.csv",
            mime="text/csv",
        )


st.caption(
    "The background water level represents the number "
    "of selected scenes, not actual stored rainwater. "
    "Demand levels are illustrative estimates. "
    "Real-world use requires suitable water treatment "
    "and compliance with local regulations."
)
