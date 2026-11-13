import streamlit as st

GLOBAL_CSS = """
<style>
  :root {
    --rw-deep: #082f24;
    --rw-green: #0e4a36;
    --rw-green-2: #1c6b4d;
    --rw-lime: #c6f36b;
    --rw-mint: #6ad3be;
    --rw-ink: #17352a;
    --rw-muted: #607267;
    --rw-line: #dfe9df;
    --rw-surface: #ffffff;
  }

  .stApp {
    background:
      radial-gradient(circle at 88% 0%, rgba(198, 243, 107, 0.18), transparent 28%),
      radial-gradient(circle at 0% 100%, rgba(106, 211, 190, 0.12), transparent 30%),
      #f5f8f3;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }

  header[data-testid="stHeader"] {
    background: transparent;
  }

  .block-container {
    max-width: 1400px;
    padding-top: 1.4rem;
    padding-bottom: 2rem;
  }

  .rw-page-header {
    position: relative;
    overflow: hidden;
    margin: 0 0 1.4rem 0;
    padding: 2.2rem 2.6rem;
    border-radius: 24px;
    color: #ffffff;
    background:
      radial-gradient(circle at 92% 10%, rgba(198, 243, 107, 0.22), transparent 24%),
      linear-gradient(135deg, #082f24 0%, #0e4a36 55%, #1c6b4d 100%);
    box-shadow: 0 18px 40px rgba(9, 50, 38, 0.16);
  }

  .rw-page-header h1 {
    margin: 0;
    color: #ffffff;
    font-size: clamp(2rem, 4vw, 3.2rem);
    font-weight: 800;
    line-height: 1.02;
    letter-spacing: -0.035em;
  }

  .rw-page-header p {
    max-width: 62rem;
    margin: 0.65rem 0 0;
    color: rgba(255, 255, 255, 0.78);
    font-size: 1rem;
    line-height: 1.55;
  }

  h2, h3 {
    color: var(--rw-ink);
    letter-spacing: -0.02em;
  }

  .stButton > button,
  .stDownloadButton > button {
    border: 0;
    border-radius: 999px;
    padding: 0.55rem 1.2rem;
    background: var(--rw-green);
    color: #ffffff;
    font-weight: 700;
    transition: transform 150ms ease, background 150ms ease;
  }

  .stButton > button:hover,
  .stDownloadButton > button:hover {
    background: var(--rw-green-2);
    color: #ffffff;
    transform: translateY(-1px);
  }

  .stButton > button[kind="primary"] {
    background: var(--rw-lime);
    color: var(--rw-deep);
  }

  .stButton > button[kind="primary"]:hover {
    background: #d5fa85;
    color: var(--rw-deep);
  }

  div[data-testid="stMetric"],
  div[data-testid="metric-container"] {
    background: var(--rw-surface);
    border: 1px solid var(--rw-line);
    border-radius: 16px;
    padding: 1rem 1.1rem;
    box-shadow: 0 8px 20px rgba(9, 50, 38, 0.05);
  }

  div[data-testid="stMetricLabel"],
  div[data-testid="metric-container"] label {
    color: var(--rw-muted);
  }

  div[data-testid="stMetricValue"],
  div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--rw-green);
    font-weight: 800;
  }

  div[data-testid="stForm"] {
    background: var(--rw-surface);
    border: 1px solid var(--rw-line);
    border-radius: 18px;
    padding: 1.2rem;
    box-shadow: 0 10px 24px rgba(9, 50, 38, 0.05);
  }

  div[data-testid="stDataFrame"] {
    background: var(--rw-surface);
    border: 1px solid var(--rw-line);
    border-radius: 14px;
    overflow: hidden;
  }

  div[data-testid="stExpander"] {
    background: var(--rw-surface);
    border: 1px solid var(--rw-line);
    border-radius: 14px;
  }

  div[data-testid="stAlert"] {
    border-radius: 12px;
  }

  div[data-baseweb="input"] > div,
  div[data-baseweb="select"] > div {
    background: var(--rw-surface);
    border-color: var(--rw-line);
    border-radius: 10px;
  }

  div[data-baseweb="input"]:focus-within > div,
  div[data-baseweb="select"]:focus-within > div {
    border-color: var(--rw-mint);
    box-shadow: 0 0 0 2px rgba(106, 211, 190, 0.18);
  }

  div[data-testid="stNumberInputContainer"] {
    border: 1px solid var(--rw-line) !important;
    border-radius: 10px !important;
    background: var(--rw-surface) !important;
    overflow: hidden;
  }

  div[data-testid="stNumberInputContainer"]:focus-within {
    border-color: var(--rw-mint) !important;
    box-shadow: 0 0 0 2px rgba(106, 211, 190, 0.18);
  }

  div[data-testid="stNumberInputContainer"] [data-baseweb="input"],
  div[data-testid="stNumberInputContainer"] [data-baseweb="base-input"],
  div[data-testid="stNumberInputContainer"] input {
    border: none !important;
    background: transparent !important;
  }

  label {
    color: var(--rw-ink);
    font-weight: 600;
  }

  hr {
    border-color: var(--rw-line);
  }

  [data-testid="stSidebarNav"] {
    display: none !important;
  }

  [data-testid="stSidebar"] {
    background:
      radial-gradient(circle at 20% 0%, rgba(198, 243, 107, 0.16), transparent 28%),
      linear-gradient(180deg, #082f24 0%, #0e4a36 65%, #1c6b4d 100%);
  }

  [data-testid="stSidebar"] * {
    color: #ffffff;
  }

  [data-testid="stSidebar"] .stButton > button {
    justify-content: flex-start;
    padding: 0.5rem 0.7rem;
    background: transparent;
    color: #ffffff;
    font-weight: 700;
    text-align: left;
  }

  [data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #ffffff;
  }

  [data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: var(--rw-lime);
    color: var(--rw-deep) !important;
    font-weight: 800;
  }

  [data-testid="stSidebar"] .stButton > button[kind="primary"] * {
    color: var(--rw-deep) !important;
  }

  [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background: #d5fa85;
    color: var(--rw-deep) !important;
  }

  [data-testid="stSidebar"] a {
    color: #ffffff !important;
    border-radius: 10px;
    padding: 0.35rem 0.5rem;
  }

  [data-testid="stSidebar"] a:hover {
    background: rgba(255, 255, 255, 0.10);
  }

  [data-testid="stSidebar"] hr {
    border-color: rgba(255, 255, 255, 0.18);
  }


  .rw-sidebar-brand {
    color: #ffffff;
    font-size: 1.5rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin: 0.6rem 0 0.15rem;
  }

  .rw-sidebar-sub {
    color: rgba(255, 255, 255, 0.68);
    font-size: 0.8rem;
    margin-bottom: 1.8rem;
  }

  .rw-nav {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .rw-nav a {
    display: block;
    padding: 0.7rem 0.8rem;
    border-radius: 10px;
    color: #ffffff !important;
    font-weight: 600;
    text-decoration: none !important;
    transition: background 140ms ease;
  }

  .rw-nav a:hover {
    background: rgba(255, 255, 255, 0.12);
  }

  .rw-nav a.active {
    background: var(--rw-lime);
    color: var(--rw-deep) !important;
    font-weight: 800;
  }

  .rw-sidebar-footer {
    color: rgba(255, 255, 255, 0.62);
    font-size: 0.78rem;
    margin-top: 1.2rem;
  }

  @media (max-width: 700px) {
    .rw-page-header {
      padding: 1.5rem 1.3rem;
      border-radius: 18px;
    }
    .rw-page-header h1 {
      font-size: 2rem;
    }
    .block-container {
      padding-left: 1rem;
      padding-right: 1rem;
    }
  }
</style>
"""


def handle_navigation():
    target = st.query_params.get("page")
    if isinstance(target, list):
        target = target[0] if target else None

    destinations = {
        "location": "pages/location.py",
        "configuration": "pages/configuration.py",
        "analysis": "pages/analysis.py",
    }
    if target in destinations:
        st.query_params.clear()
        st.switch_page(destinations[target])


def inject_theme():
    handle_navigation()
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="rw-page-header"><h1>{title}</h1>{subtitle_html}</div>',
        unsafe_allow_html=True,
    )


def render_sidebar(current_page: str):
    with st.sidebar:
        st.markdown(
            '<div class="rw-sidebar-brand">💧 RainWise</div>'
            '<div class="rw-sidebar-sub">Smart Rainwater Planning</div>',
            unsafe_allow_html=True,
        )

        st.page_link("pages/location.py", label="Location & Rainfall")
        st.page_link("pages/configuration.py", label="Configuration")
        st.page_link("pages/analysis.py", label="Analysis")

        st.markdown(
            f"""
<style>
  [data-testid="stSidebar"] a[href="/{current_page}"],
  [data-testid="stSidebar"] a[href="/{current_page}"] * {{
    background: var(--rw-lime) !important;
    color: var(--rw-deep) !important;
    font-weight: 800 !important;
    border-radius: 10px !important;
  }}
</style>
""",
            unsafe_allow_html=True,
        )

        st.divider()
        st.caption("INT6181 Python Group Project")
