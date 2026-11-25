# Rainwater Smart Planner

A smart rainwater harvesting and 7-day water scheduling app. Based on the Open-Meteo 7-day rainfall forecast, it simulates the daily water balance of a rooftop tank and, after exhaustively searching all valid schedules, produces an intelligent task plan with zero shortfall for high-priority usage. **No external runtime dependencies beyond the weather API.**

## Environment Setup

| Item | Requirement |
| --- | --- |
| Python | 3.10 or newer (3.12 recommended — the version used in CI) |
| pip | Bundled with Python; upgrading first is recommended: `python -m pip install --upgrade pip` |
| OS | Windows / macOS / Linux (a one-click launcher script is provided for Windows) |
| Network | Geolocation and the 7-day rainfall forecast require internet access to Open-Meteo (free, no API key needed); all other features work offline |
| Browser | Any modern browser; GPS geolocation requires granting location permission in the browser prompt (available only on `localhost` or HTTPS pages) |

Python dependencies (`requirements.txt`):

| Package | Version | Purpose |
| --- | --- | --- |
| `streamlit` | ≥ 1.67 | Web UI framework; the interface uses `streamlit.components.v2` custom components — older versions raise `ModuleNotFoundError` |
| `pandas` | ≥ 2.0 | Result tables and CSV export |
| `streamlit-js-eval` | ≥ 1.0 | Browser GPS geolocation (preferred) |
| `streamlit-geolocation` | ≥ 0.0.10 | Browser GPS geolocation (fallback — either package works, the code falls back automatically) |
| `pytest` | ≥ 7.4 | Running the unit tests (development/verification only) |

## How to Run

**Option 1: Command line (all platforms)**

```bash
# 1. (Optional) Create a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Run the unit tests to verify the setup
pytest -q

# 4. Start the app
streamlit run main.py
```

Your browser should open `http://localhost:8501` automatically; if it does not, visit that address manually. To stop the app, press `Ctrl + C` in the terminal.

**Option 2: Windows one-click launch**

Simply double-click `WebClick.bat`: the script locates a Python interpreter on your machine (Anaconda first, then the `py` launcher / system `python`), checks for and auto-installs missing dependencies, then starts the app.

**Troubleshooting**

- `ModuleNotFoundError: No module named 'streamlit.components.v2'` on startup: your Streamlit is too old — run `pip install -U "streamlit>=1.67"`.
- `No module named 'streamlit_js_eval'` on startup: run `pip install -r requirements.txt`; a fallback is built in, so having either geolocation package is enough.
- Geolocation / rainfall data fails to load: check that your network can reach Open-Meteo, and that the browser is allowed to access your location.

## Features

- **Welcome screen**: fullscreen custom component; click to enter the main interface. No flickering animations.
- **Dual-mode geolocation**: browser GPS (permission requested only after clicking) or global city search (Open-Meteo geocoding, with disambiguation for duplicate city names).
- **7-day rainfall cards**: no-rain / light / moderate / heavy rain animations and millimetre values graded by precipitation, with the data fetch timestamp shown.
- **Six usage scenes**: Bathroom, Kitchen, Laundry, Garden, Driveway, Living Room — each with a baseline amount, priority, and "fixed daily / flexible one-off" attribute; Low / Medium / High levels scale usage by 0.6 / 1.0 / 1.5.
- **Tank parameters**: collection area and tank capacity, plus advanced settings for collection efficiency, initial storage, and minimum reserve; invalid combinations (initial storage exceeding capacity) produce a clear error message.
- **Smart scheduling results**: four metric cards (collected / allocated / shortfall / overflow), baseline vs. optimized plan comparison, day-by-day 7-day schedule, tank storage curve, collection-vs-allocation bar chart, tiered text recommendations, and one-click CSV export.
- **Result parameter annotation**: the results section shows the exact location, tank parameters, and per-scene usage amounts used in the calculation, so you can verify the inputs behind every result.

## Project Structure

| File | Responsibility |
| --- | --- |
| `rainfall_service.py` | Open-Meteo city search and 7-day precipitation forecast fetching, with input validation and network error handling |
| `rainwater_engine.py` | Pure-Python core engine: daily water-balance simulation and exhaustive schedule optimization; no Streamlit dependency |
| `recommendation_engine.py` | Compares baseline and optimized plans to generate shortfall / overflow / task-adjustment recommendations |
| `main.py` | Streamlit single-page interface — presentation and engine calls only |
| `test_rainwater.py` / `test_recommendation.py` | pytest unit tests for the core engine and recommendation generation |
| `assets/` | Scene card images |

`water_engine.py`, `data/`, and `test_water_engine.py` are legacy code and tests from an earlier iteration (a tiered water-bill calculator). They still pass all tests and are kept for reference; even earlier page implementations live in `archive/`.

## Core Engine API

- `run_schedule(rainfall, area, capacity, tasks, schedule, ...)`: simulates the full seven days for a given schedule, computing daily collection, overflow (beyond capacity), priority-ordered allocation, shortfall, and remaining storage.
- `baseline_schedule(tasks)`: the baseline plan — flexible tasks are placed on the last day of their allowed window.
- `compare_strategies(rainfall, area, capacity, tasks, ...)`: exhaustively enumerates all date combinations for flexible tasks (capped at 50,000) and picks the optimum by lexicographic score: ① high-priority shortfall → ② total shortfall → ③ total overflow → ④ number of schedule changes. Returns complete simulation results for both the baseline and the optimized plan.
- `generate_recommendations(comparison, dates, tasks)`: generates text recommendations from the differences between the two plans.

`WaterTask` fields: `name`, `amount` (litres), `priority` (1 = highest), `flexible`, `earliest_day` / `latest_day`. Invalid inputs (empty rainfall series, negative area, efficiency outside [0,1], task window out of range, fixed tasks spanning multiple days, etc.) raise `ValueError`.

## Daily Water-Balance Formulas

```
Collected (L)  = rainfall (mm) × collection area (m²) × collection efficiency
Overflow (L)   = max(0, previous storage + collected − tank capacity)
Available (L)  = current storage − minimum reserve
Allocation     = tasks served in (priority, scene order); any unmet amount is recorded as shortfall
```

## Notes

Rainfall data comes from the Open-Meteo 7-day forecast; baseline usage amounts are demo estimates. The background water-level animation reflects the number of selected scenes, not actual storage. CI is provided by GitHub Actions and runs the full pytest suite automatically on push and pull requests.
