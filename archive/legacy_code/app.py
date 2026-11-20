import streamlit as st

from theme import inject_theme

st.set_page_config(
    page_title="RainWise",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)


inject_theme()

HERO = """
<style>
  header[data-testid="stHeader"] { display: none !important; }
  section[data-testid="stSidebar"] { display: none !important; }
  [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    overflow: hidden !important;
  }
  .block-container {
    max-width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
  }
  .stMarkdown { margin: 0 !important; }

  .rw-hero {
    position: relative;
    min-height: 100vh;
    width: 100%;
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 2rem;
    align-items: center;
    padding: clamp(2rem, 5vw, 5rem) clamp(2rem, 6vw, 7rem);
    box-sizing: border-box;
    border-radius: 0;
    overflow: hidden;
    color: #ffffff;
    background:
      radial-gradient(circle at 88% 18%, rgba(194, 245, 112, 0.22), transparent 26%),
      radial-gradient(circle at 10% 90%, rgba(106, 211, 190, 0.20), transparent 30%),
      linear-gradient(135deg, #082f24 0%, #0e4a36 52%, #1c6b4d 100%);
    box-shadow: none;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }

  .rw-hero:before {
    content: "";
    position: absolute;
    inset: 0;
    background:
      linear-gradient(115deg, transparent 0 55%, rgba(255,255,255,0.04) 55% 56%, transparent 56%),
      linear-gradient(65deg, transparent 0 72%, rgba(255,255,255,0.035) 72% 73%, transparent 73%);
    pointer-events: none;
  }

  .rw-copy {
    position: relative;
    z-index: 2;
  }

  .rw-brand {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    margin-bottom: 2.2rem;
    font-size: 1.05rem;
    font-weight: 800;
    letter-spacing: -0.02em;
  }

  .rw-dot {
    width: 34px;
    height: 34px;
    display: grid;
    place-items: center;
    border-radius: 50%;
    background: linear-gradient(145deg, #c6f36b, #6ad3be);
    box-shadow: 0 8px 24px rgba(198, 243, 107, 0.28);
    font-size: 1rem;
  }

  .rw-kicker {
    margin-bottom: 0.4rem;
    color: #c6f36b;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }

  .rw-title {
    margin: 0.5rem 0 1.3rem;
    color: #ffffff;
    font-size: clamp(2.8rem, 5vw, 5.4rem);
    font-weight: 800;
    line-height: 0.95;
    letter-spacing: -0.055em;
  }

  .rw-title span {
    color: #c6f36b;
  }

  .rw-sub {
    max-width: 38rem;
    margin: 0;
    color: rgba(255, 255, 255, 0.82);
    font-size: clamp(1rem, 1.35vw, 1.22rem);
    line-height: 1.65;
  }

  .rw-cta {
    display: inline-flex;
    align-items: center;
    gap: 0.7rem;
    margin-top: 2rem;
    padding: 0.9rem 1.35rem;
    border-radius: 999px;
    background: #c6f36b;
    color: #082f24 !important;
    font-size: 1rem;
    font-weight: 800;
    text-decoration: none !important;
    box-shadow: 0 12px 28px rgba(198, 243, 107, 0.22);
    transition: transform 160ms ease, box-shadow 160ms ease;
  }

  .rw-cta:hover {
    transform: translateY(-2px);
    box-shadow: 0 16px 34px rgba(198, 243, 107, 0.30);
  }

  .rw-points {
    display: flex;
    flex-wrap: wrap;
    gap: 1.4rem;
    margin-top: 2.7rem;
    color: rgba(255, 255, 255, 0.68);
    font-size: 0.85rem;
  }

  .rw-points b {
    color: #ffffff;
    margin-right: 0.35rem;
  }

  .rw-visual {
    position: relative;
    z-index: 1;
    min-height: 430px;
  }

  .rw-ring {
    position: absolute;
    top: 50%;
    left: 50%;
    width: min(32vw, 410px);
    height: min(32vw, 410px);
    transform: translate(-50%, -50%);
    border: 1px solid rgba(198, 243, 107, 0.35);
    border-radius: 50%;
    box-shadow:
      0 0 0 42px rgba(198, 243, 107, 0.05),
      0 0 0 84px rgba(198, 243, 107, 0.03);
  }

  .rw-drop {
    position: absolute;
    top: 50%;
    left: 50%;
    width: min(18vw, 230px);
    transform: translate(-50%, -50%);
    filter: drop-shadow(0 28px 34px rgba(0, 0, 0, 0.22));
    animation: rw-float 5s ease-in-out infinite;
  }

  @keyframes rw-float {
    0%, 100% { transform: translate(-50%, -50%); }
    50% { transform: translate(-50%, -54%); }
  }

  .rw-card {
    position: absolute;
    min-width: 150px;
    padding: 0.8rem 1rem;
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.10);
    backdrop-filter: blur(12px);
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
  }

  .rw-card span {
    display: block;
    margin-bottom: 0.18rem;
    color: rgba(255, 255, 255, 0.60);
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .rw-card strong {
    color: #ffffff;
    font-size: 1rem;
  }

  .rw-card.one { top: 7%; left: 0; }
  .rw-card.two { right: 0; bottom: 18%; }
  .rw-card.three { left: 4%; bottom: 3%; }

  @media (max-width: 900px) {
    .rw-hero {
      grid-template-columns: 1fr;
      min-height: 100vh;
      padding: 2.2rem 1.6rem;
    }
    .rw-visual { display: none; }
    .rw-title { font-size: clamp(2.5rem, 12vw, 4rem); }
    .rw-sub { font-size: 1rem; }
    .rw-points { gap: 0.8rem; margin-top: 1.6rem; }
  }
</style>

<div class="rw-hero">
  <div class="rw-copy">
    <div class="rw-brand"><span class="rw-dot">💧</span> RainWise</div>
    <div class="rw-kicker">Smart rainwater planning</div>
    <h1 class="rw-title">Make every<br/><span>drop count.</span></h1>
    <p class="rw-sub">
      See how much rainwater you can collect, how to allocate it across your
      household, and what to change when supply runs short or the tank overflows.
    </p>
    <a class="rw-cta" href="?page=location" target="_self">Enter RainWise <span>→</span></a>
    <div class="rw-points">
      <span><b>01</b> Collect</span>
      <span><b>02</b> Allocate</span>
      <span><b>03</b> Improve</span>
    </div>
  </div>
  <div class="rw-visual">
    <div class="rw-ring"></div>
    <div class="rw-drop">
      <svg viewBox="0 0 220 250" width="100%" role="img" aria-label="Water drop">
        <defs>
          <linearGradient id="rwWater" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#c6f36b"/>
            <stop offset="50%" stop-color="#6ad3be"/>
            <stop offset="100%" stop-color="#2b8e9e"/>
          </linearGradient>
        </defs>
        <path d="M110 8C110 8 38 98 38 156a72 72 0 0 0 144 0C182 98 110 8 110 8Z"
              fill="url(#rwWater)"/>
        <ellipse cx="83" cy="150" rx="18" ry="28" fill="rgba(255,255,255,0.28)"
                 transform="rotate(-22 83 150)"/>
      </svg>
    </div>
    <div class="rw-card one"><span>Rainfall</span><strong>Local data</strong></div>
    <div class="rw-card two"><span>Garden</span><strong>70% covered</strong></div>
    <div class="rw-card three"><span>Overflow</span><strong>300 L saved</strong></div>
  </div>
</div>
"""

st.markdown(HERO, unsafe_allow_html=True)
