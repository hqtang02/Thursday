"""SmartWater Optimizer —— 智慧水費與節水優化器界面。

本文件只負責交互與展示，所有計算均委託給 ``water_engine``。
運行：``streamlit run main.py``
"""

from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urlencode

import folium
import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as st_component_html

from water_engine import (
    analyze_usage_breakdown,
    calculate_tiered_bill,
    check_drought_status,
    generate_conservation_plan,
    load_config,
)

st.set_page_config(
    page_title="SmartWater Optimizer",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# 雙語字典（預設繁體中文）
# ---------------------------------------------------------------------------

LANGUAGES: Dict[str, str] = {"zh-TW": "繁中", "en": "English"}

_S2T_SIMP = (
    "两侣双与严个为举义习于仅从价优伦关内冲减划别务动匀区单卫历压厕参号后"
    "启块处头学实对币带并库开张当径态总惯执抛损换据摊数断无时机条"
    "来构标档检横测满点状独础确种称穷类紧红级纯线组结络绝缓缩网节"
    "补计认识该误请读调贝负账费赖载较输边达过运进适选递采钟钱错键"
    "长闭间阈阶际随项顺须预频额饪饮马验齐龙余干洒"
)
_S2T_TRAD = (
    "兩侶雙與嚴個為舉義習於僅從價優倫關內沖減劃別務動勻區單衛歷壓廁參號後"
    "啟塊處頭學實對幣帶並庫開張當徑態總慣執拋損換據攤數斷無時機條"
    "來構標檔檢橫測滿點狀獨礎確種稱窮類緊紅級純線組結絡絕緩縮網節"
    "補計認識該誤請讀調貝負帳費賴載較輸邊達過運進適選遞採鐘錢錯鍵"
    "長閉間閾階際隨項順須預頻額飪飲馬驗齊龍餘乾灑"
)
_S2T = dict(zip(_S2T_SIMP, _S2T_TRAD))


def to_traditional(text: str) -> str:
    """把簡體字段轉換為繁體顯示（未收錄字原樣保留）。"""
    return "".join(_S2T.get(char, char) for char in text)


STRINGS: Dict[str, Dict[str, str]] = {
    "app_name": {"zh-TW": "智慧水費與節水優化器", "en": "SmartWater Optimizer"},
    "landing_kicker": {"zh-TW": "智慧水費規劃", "en": "SMART WATER PLANNING"},
    "landing_pre": {"zh-TW": "告別", "en": "Beat the "},
    "landing_em": {"zh-TW": "天價水費。", "en": "water bill."},
    "landing_desc": {
        "zh-TW": (
            "用本地階梯水價與歷史降水資料，拆解家庭用水、預警供水緊張，"
            "並挑出舒適度折損最小的省錢行動。所有計算均在本機完成。"
        ),
        "en": (
            "Break down household usage, warn about dry supply months and find "
            "the cheapest savings plan with the least lifestyle compromise — "
            "all computed locally from bundled data."
        ),
    },
    "landing_enter": {"zh-TW": "進入優化器", "en": "Enter the Optimizer"},
    "back": {"zh-TW": "返回首頁", "en": "Back to home"},
    "console_location": {"zh-TW": "① 地點與月份", "en": "1  Location & Month"},
    "console_lifestyle": {"zh-TW": "② 生活類型", "en": "2  Lifestyle"},
    "console_result": {"zh-TW": "③ 計算結果", "en": "3  Results"},
    "next_lifestyle": {"zh-TW": "下一步：生活類型 →", "en": "Next: Lifestyle →"},
    "next_result": {"zh-TW": "下一步：計算結果 →", "en": "Next: Results →"},
    "lifestyle_hint": {
        "zh-TW": "先點選一個生活畫像，再用下方滑桿微調。",
        "en": "Pick a profile first, then fine-tune with the sliders below.",
    },
    "city_label": {"zh-TW": "城市 / 地區", "en": "City / Region"},
    "month_label": {"zh-TW": "月份", "en": "Month"},
    "month_unit": {"zh-TW": "月", "en": ""},
    "rain_light": {"zh-TW": "小雨", "en": "Light rain"},
    "rain_moderate": {"zh-TW": "中雨", "en": "Moderate rain"},
    "rain_heavy": {"zh-TW": "大雨", "en": "Heavy rain"},
    "month_hint": {
        "zh-TW": "滑過月份可依降水量播放雨勢動畫，點擊切換月份。",
        "en": "Hover a month for a rainfall animation; click to switch months.",
    },
    "map_title": {"zh-TW": "地點預覽", "en": "Location preview"},
    "map_caption": {
        "zh-TW": "地圖底圖需連線載入；切換城市後會即時更新位置。所有水費與降水計算仍完全離線。",
        "en": "Map tiles need an internet connection; the map updates immediately when the city changes. All bill and rainfall calculations stay offline.",
    },
    "tariff_caption": {
        "zh-TW": "目前階梯：{name}（{months} 個月帳單週期）",
        "en": "Current tariff: {name} ({months}-month cycle)",
    },
    "preset_title": {
        "zh-TW": "一鍵套用使用者畫像",
        "en": "One-click user profiles",
    },
    "preset_caption": {
        "zh-TW": "點擊後自動填入全部參數，再用下方滑桿微調。",
        "en": "Click to fill all parameters, then fine-tune with the sliders below.",
    },
    "params_title": {"zh-TW": "調整你的日常用水", "en": "Adjust your daily usage"},
    "people": {"zh-TW": "家庭成員人數", "en": "Household members"},
    "shower": {"zh-TW": "每日淋浴分鐘數（每人）", "en": "Shower minutes per person per day"},
    "laundry": {"zh-TW": "每週洗衣次數", "en": "Laundry loads per week"},
    "dish": {"zh-TW": "洗碗習慣", "en": "Dishwashing habit"},
    "target": {
        "zh-TW": "期望每月省下多少錢（{currency}）",
        "en": "Target monthly savings ({currency})",
    },
    "overview": {"zh-TW": "帳單概覽", "en": "Bill overview"},
    "total_bill": {
        "zh-TW": "預計 1 個月總水費",
        "en": "Estimated 1-month bill",
    },
    "tier": {"zh-TW": "目前階梯檔位", "en": "Current tariff tier"},
    "tier_value": {"zh-TW": "第 {n} 檔", "en": "Tier {n}"},
    "savings": {"zh-TW": "潛在可省金額", "en": "Potential savings"},
    "next_tier": {
        "zh-TW": "距離第 {n} 檔漲價臨界點還差 {m3:.2f} m³（共 {total:.2f} m³ / 每日 {liters:.0f} L）。",
        "en": "{m3:.2f} m³ until tier {n} pricing kicks in ({total:.2f} m³ total / {liters:.0f} L per day).",
    },
    "top_tier": {
        "zh-TW": "已處於最高階梯，節水可直接按最高單價省錢。",
        "en": "You are in the top tier — every litre saved is billed at the highest rate.",
    },
    "breakdown": {"zh-TW": "用水結構拆解", "en": "Usage breakdown"},
    "volume_col": {"zh-TW": "用水量 (m³/期)", "en": "Volume (m³/cycle)"},
    "villain": {
        "zh-TW": "費水刺客：{name}，佔 {pct:.1f}%。",
        "en": "Biggest water hog: {name} at {pct:.1f}%.",
    },
    "quota_line": {"zh-TW": "紅線 {quota:.0f} L/人/日", "en": "Red line {quota:.0f} L/person/day"},
    "normal_supply": {"zh-TW": "供水正常", "en": "Supply normal"},
    "quota_note": {
        "zh-TW": "每日安全配額：{note}",
        "en": "Safe daily quota: {note}",
    },
    "drought_note": {
        "zh-TW": (
            "供水緊張期：全家每日安全紅線約 {quota:,.0f} L，"
            "目前估算 {usage:,.0f} L。節省目標已自動增加 10% 安全邊際。"
        ),
        "en": (
            "Dry-supply period: household red line is about {quota:,.0f} L/day "
            "versus an estimated {usage:,.0f} L/day. The savings target includes "
            "a 10% safety margin."
        ),
    },
    "actions": {"zh-TW": "低折損節水行動清單", "en": "Low-effort conservation actions"},
    "saved_day": {"zh-TW": "省水/日", "en": "Saved/day"},
    "saved_cycle": {"zh-TW": "省下/期", "en": "Saved/cycle"},
    "comfort_cost": {"zh-TW": "舒適度 -{n}", "en": "Comfort -{n}"},
    "no_action": {
        "zh-TW": "目前沒有需要額外執行的節水措施，或帳單已在免費檔。",
        "en": "No additional actions are needed for this target, or the bill is already in the free tier.",
    },
    "total_comfort": {"zh-TW": "總舒適度折損", "en": "Total comfort cost"},
    "water_saved": {"zh-TW": "節水總量", "en": "Total water saved"},
    "goal_met": {
        "zh-TW": "這套組合預計每月省下 {symbol}{actual:.2f}，達成 {symbol}{target:.0f} 的目標，每月帳單降至 {symbol}{bill:.2f}。",
        "en": "This plan saves {symbol}{actual:.2f} per month, meets the {symbol}{target:.0f} goal and lowers the monthly bill to {symbol}{bill:.2f}.",
    },
    "goal_missed": {
        "zh-TW": "現有措施每月最多可省 {symbol}{actual:.2f}，距目標仍差 {symbol}{gap:.2f}；已給出最大努力方案。",
        "en": "The current measure library saves at most {symbol}{actual:.2f} per month, leaving a {symbol}{gap:.2f} gap. A best-effort plan is shown.",
    },
    "data_note": {
        "zh-TW": "階梯水價與降水資料為示範用本地知識庫，請以當地水務機構公告為準。",
        "en": "Tariff and rainfall data are bundled for demonstration; check your local water authority for actual bills.",
    },
    "source_note": {
        "zh-TW": "資料來源：本機知識庫，執行時不呼叫外部 API。",
        "en": "Source: local knowledge base; no external API calls at runtime.",
    },
}


def t(key: str, lang: str, **kwargs: Any) -> str:
    """按語言返回界面文案。"""
    template = STRINGS[key][lang]
    return template.format(**kwargs) if kwargs else template


def localized(zh: str, en: str | None, lang: str) -> str:
    """按語言返回配置中的中英文字段。"""
    if lang == "en":
        return en or to_traditional(zh)
    return to_traditional(zh)


# ---------------------------------------------------------------------------
# 高對比度樣式（所有文字/背景組合 ≥ 7:1）
# ---------------------------------------------------------------------------

CSS = """
<style>
  :root {
    --sw-ink: #14352c;        /* 13.33:1 on white */
    --sw-muted: #3f544b;      /* 8.14:1 on white, 7.66:1 on app bg */
    --sw-soft: #35493f;       /* 9.65:1 on white */
    --sw-green: #0a5c4a;      /* 7.95:1 on white */
    --sw-blue: #1e40af;       /* 7.75:1 on pastel */
    --sw-line: #c7d8ce;
    --sw-surface: #ffffff;
    --sw-app: #f5f9f6;
  }
  .stApp {
    background: var(--sw-app);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    color: var(--sw-ink);
  }
  .block-container { max-width: 1320px; padding-top: 1.2rem; padding-bottom: 3rem; }
  header[data-testid="stHeader"] { background: transparent; }
  section[data-testid="stSidebar"] { display: none; }

  label, .stMarkdown, .stText, [data-testid="stCaptionContainer"],
  [data-testid="stCaptionContainer"] p, .stSlider label, .stSelectbox label {
    color: var(--sw-ink) !important;
  }
  [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
    color: var(--sw-muted) !important;
  }
  div[data-testid="stMetricLabel"] { color: var(--sw-muted) !important; }
  div[data-testid="stMetricValue"] { color: var(--sw-green) !important; font-weight: 800; }
  div[data-testid="stMetric"] {
    background: var(--sw-surface);
    border: 1px solid var(--sw-line);
    border-radius: 16px;
    padding: 1rem 1.1rem;
    box-shadow: 0 8px 20px rgba(9,50,38,0.05);
  }
  .stButton > button {
    border: 1px solid var(--sw-green);
    border-radius: 999px;
    background: var(--sw-surface);
    color: var(--sw-green);
    font-weight: 700;
    white-space: nowrap !important;
  }
  .stButton > button[kind="primary"] {
    background: var(--sw-green);
    color: #ffffff;
    border-color: var(--sw-green);
  }
  .stButton > button:hover { background: #f4faf6; color: var(--sw-green); }
  .stButton > button[kind="primary"]:hover { background: #08493a; color: #ffffff; }

  /* 頂部品牌列 */
  .sw-topbar { padding: 0.2rem 0 1rem; }
  .sw-brand { color: var(--sw-ink); font-size: 1.02rem; font-weight: 800; letter-spacing: -0.02em; }
  .sw-brand span { color: var(--sw-green); }

  /* Landing：參考簡報風格的柔和漸層卡片，無動效 */
  .sw-landing {
    min-height: 66vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3.5rem 2rem 4.5rem;
    border-radius: 26px;
    text-align: center;
    background: linear-gradient(
      115deg,
      #eee9fb 0%,
      #fbf4e4 32%,
      #e8f7e2 66%,
      #e1f3fb 100%
    );
  }
  .sw-landing-kicker { color: var(--sw-soft); font-size: 0.86rem; font-weight: 600; letter-spacing: 0.08em; }
  .sw-landing h1 {
    margin: 1.1rem 0 0.9rem;
    color: var(--sw-ink);
    font-size: clamp(2.4rem, 5.6vw, 4.4rem);
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -0.05em;
  }
  .sw-landing h1 em { color: var(--sw-blue); font-style: normal; }
  .sw-landing p { max-width: 40rem; margin: 0; color: var(--sw-soft); font-size: 1rem; line-height: 1.65; }
  .sw-enter {
    display: inline-flex; align-items: center; justify-content: center;
    margin-top: 3.2rem; padding: 0.78rem 1.9rem;
    border-radius: 999px; background: var(--sw-ink);
    color: #ffffff !important;
    font-size: 1rem; font-weight: 700; text-decoration: none;
  }
  .sw-enter:hover { background: #0a251c; color: #ffffff !important; }

  /* Console */
  .sw-console { padding: 0.1rem 0 0.6rem; }
  .sw-console-label { color: var(--sw-muted); font-size: 0.74rem; font-weight: 700; letter-spacing: 0.1em; }

  /* App hero */
  .sw-hero {
    display: flex; align-items: center; justify-content: space-between; gap: 2rem;
    padding: 1.6rem 2rem; border-radius: 20px; color: #ffffff;
    background:
      radial-gradient(circle at 88% 12%, rgba(227,255,160,0.22), transparent 26%),
      linear-gradient(125deg, #062a20 0%, #084635 58%, #0a5a44 100%);
  }
  .sw-hero h1 { margin: 0.3rem 0 0.4rem; font-size: clamp(1.6rem, 2.8vw, 2.3rem); letter-spacing: -0.04em; color: #ffffff; }
  .sw-hero p { margin: 0; color: #eaf4ee; font-size: 0.9rem; }
  .sw-hero-stat { min-width: 175px; padding: 0.9rem 1.1rem; border: 1px solid #7fb59c; border-radius: 14px; background: #062a20; text-align: center; }
  .sw-hero-stat span { display: block; color: #eaf4ee; font-size: 0.76rem; }
  .sw-hero-stat strong { display: block; margin: 0.25rem 0; color: #ffffff; font-size: 2.1rem; line-height: 1; }

  /* Alerts */
  .sw-alert { margin: 0.8rem 0; padding: 0.9rem 1.1rem; border-radius: 12px; font-weight: 600; line-height: 1.55; }
  .sw-alert.ok { background: #eaf7dc; color: #224412; border: 1px solid #7ba95a; }
  .sw-alert.warn { background: #fff4dc; color: #503402; border: 1px solid #c79a3a; }
  .sw-alert.crit { background: #ffeae6; color: #6e241a; border: 1px solid #c4695a; }
  .sw-alert.info { background: #e7f1ec; color: #14352c; border: 1px solid #7fb59c; }

  .sw-section { margin: 1.5rem 0 0.7rem; padding-bottom: 0.45rem; border-bottom: 1px solid var(--sw-line); }
  .sw-section h2 { color: var(--sw-ink); letter-spacing: -0.025em; }

  /* Month cells: native Streamlit buttons styled as cards, hover shows rain */
  .sw-months { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 6px; }
  div[data-testid="column"]:has(.sw-month-rain) {
    position: relative; padding: 0.45rem 0.1rem;
    border: 1px solid var(--sw-line); border-radius: 10px;
    background: var(--sw-surface); text-align: center;
  }
  div[data-testid="column"]:has(.sw-month-rain.active) {
    background: var(--sw-green); border-color: var(--sw-green);
  }
  div[data-testid="column"]:has(.sw-month-rain) button {
    width: 100%; margin: 0; padding: 0; border: 0; border-radius: 0;
    background: transparent !important; box-shadow: none !important;
    color: var(--sw-ink) !important; font-weight: 800; font-size: 0.9rem;
    white-space: nowrap !important;
  }
  div[data-testid="column"]:has(.sw-month-rain.active) button {
    color: #ffffff !important;
  }
  div[data-testid="column"]:has(.sw-month-rain) button:hover {
    background: transparent !important;
  }
  .sw-month-rain {
    display: block; margin-top: 0.15rem;
    color: var(--sw-muted); font-size: 0.7rem; font-weight: 600;
  }
  .sw-month-rain.active { color: #ffffff; }
  .sw-tip {
    display: none; position: absolute; top: calc(100% + 8px); left: 50%;
    transform: translateX(-50%); width: 186px; z-index: 60; padding: 0.65rem;
    border: 1px solid #7fb59c; border-radius: 14px; background: #062a20; color: #ffffff;
    box-shadow: 0 14px 30px rgba(6,42,32,0.3);
  }
  div[data-testid="column"]:has(.sw-month-rain):has(:is(button, .sw-month-rain):hover) .sw-tip { display: block; }
  .sw-tip.align-left { left: 0; transform: none; }
  .sw-tip.align-right { left: auto; right: 0; transform: none; }
  .sw-tip-head { margin-bottom: 0.5rem; color: #eaf4ee; font-size: 0.74rem; font-weight: 700; text-align: center; }
  .sw-rain-scene { height: 92px; overflow: hidden; border-radius: 10px; background: linear-gradient(180deg, #0b4535, #062a20); }
  .sw-rain-svg { display: block; width: 100%; height: 92px; }
  .sw-cloud { fill: none; stroke: var(--sw-accent, #e3ffa0); stroke-width: 6; stroke-linecap: round; stroke-linejoin: round; }
  .sw-drop { stroke: #8fe0ff; stroke-linecap: round; opacity: 0; animation: sw-fall 1s linear infinite; }
  .sw-tip.light .sw-drop { stroke-width: 5; animation-duration: 1.5s; }
  .sw-tip.light .sw-drop:nth-of-type(n+4) { display: none; }
  .sw-tip.moderate .sw-drop { stroke-width: 6; animation-duration: 0.85s; }
  .sw-tip.moderate .sw-drop:nth-of-type(n+7) { display: none; }
  .sw-tip.heavy .sw-drop { stroke-width: 7; animation-duration: 0.42s; }
  .sw-tip.heavy .sw-flash { opacity: 1; }
  .sw-flash { fill: #e3ffa0; font-size: 15px; opacity: 0; }
  @keyframes sw-fall {
    0% { opacity: 0; transform: translateY(-8px); }
    20% { opacity: 1; }
    100% { opacity: 0; transform: translateY(12px); }
  }

  /* Donut + legend */
  .sw-donut-wrap { display: flex; align-items: center; gap: 1.4rem; padding: 1.1rem; border: 1px solid var(--sw-line); border-radius: 16px; background: var(--sw-surface); }
  .sw-donut { position: relative; flex: 0 0 auto; width: 148px; height: 148px; border-radius: 50%; }
  .sw-donut-hole { position: absolute; inset: 26px; display: flex; flex-direction: column; align-items: center; justify-content: center; border-radius: 50%; background: var(--sw-surface); text-align: center; }
  .sw-donut-hole span { color: var(--sw-muted); font-size: 0.68rem; }
  .sw-donut-hole strong { color: var(--sw-ink); font-size: 1rem; }
  .sw-legend-row { display: flex; align-items: center; gap: 0.55rem; margin: 0.42rem 0; color: var(--sw-ink); font-size: 0.85rem; }
  .sw-dot { width: 10px; height: 10px; border-radius: 50%; flex: 0 0 auto; }
  .sw-legend-row b { margin-left: auto; font-variant-numeric: tabular-nums; }

  /* Action list */
  .sw-action {
    display: grid; grid-template-columns: minmax(0, 1fr) 92px 104px 104px;
    align-items: center; gap: 0.8rem; margin-bottom: 0.55rem; padding: 0.85rem 1rem;
    border: 1px solid var(--sw-line); border-left: 4px solid var(--sw-green);
    border-radius: 13px; background: var(--sw-surface);
  }
  .sw-action-title { color: var(--sw-ink); font-weight: 700; font-size: 0.92rem; }
  .sw-action-sub { margin-top: 0.18rem; color: var(--sw-muted); font-size: 0.76rem; }
  .sw-action-stat { text-align: right; }
  .sw-action-stat span { display: block; color: var(--sw-muted); font-size: 0.69rem; }
  .sw-action-stat strong { color: var(--sw-green); font-size: 0.95rem; font-variant-numeric: tabular-nums; }
  .sw-badge { justify-self: end; padding: 0.3rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 800; white-space: nowrap; }
  .sw-badge.low { background: #eaf7dc; color: #224412; }
  .sw-badge.mid { background: #fff4dc; color: #503402; }
  .sw-badge.high { background: #ffeae6; color: #6e241a; }

  @media (max-width: 900px) {
    .sw-landing { min-height: 58vh; padding: 2.2rem 1.2rem 3rem; }
    .sw-months { grid-template-columns: repeat(6, minmax(0, 1fr)); }
    .sw-action { grid-template-columns: 1fr 80px 80px; }
  }
</style>
"""

CURRENCY_SYMBOLS: Dict[str, str] = {"HKD": "HK$", "CNY": "¥", "GBP": "£"}
DONUT_COLORS: List[str] = ["#0a5c4a", "#237a60", "#3f9c7c", "#7ec9a8", "#b6e07a"]
VIEWS: List[str] = ["location", "lifestyle", "result"]

# 透過 URL 傳遞的狀態（僅首頁進入連結使用；月份切換已改為原生按鈕，不再整頁重載）
STATE_KEYS: List[str] = [
    "entered", "view", "lang", "city", "month", "people",
    "shower_minutes_per_day", "laundry_loads_per_week", "dishwashing_habit",
    "target_savings", "drinking_cooking_liters_per_person_per_day",
    "toilet_flushes_per_person_per_day",
]
INT_KEYS = {"month", "people"}
FLOAT_KEYS = {
    "shower_minutes_per_day", "laundry_loads_per_week", "target_savings",
    "drinking_cooking_liters_per_person_per_day",
    "toilet_flushes_per_person_per_day",
}

RAIN_SVG = """
<svg class="sw-rain-svg" viewBox="0 0 200 130" aria-hidden="true">
  <path class="sw-cloud" d="M48 84 C34 84 26 73 29 61 C32 49 45 44 56 50 C59 30 76 18 95 24 C111 14 134 23 138 44 C154 42 166 53 165 66 C164 78 153 85 141 85 L56 85 C53 85 50 85 48 84 Z"/>
  <line class="sw-drop" x1="60" y1="92" x2="60" y2="112"/>
  <line class="sw-drop" x1="80" y1="88" x2="80" y2="118"/>
  <line class="sw-drop" x1="100" y1="94" x2="100" y2="110"/>
  <line class="sw-drop" x1="120" y1="90" x2="120" y2="122"/>
  <line class="sw-drop" x1="70" y1="98" x2="70" y2="114"/>
  <line class="sw-drop" x1="110" y1="96" x2="110" y2="116"/>
  <line class="sw-drop" x1="90" y1="100" x2="90" y2="112"/>
  <line class="sw-drop" x1="132" y1="94" x2="132" y2="110"/>
  <line class="sw-drop" x1="50" y1="96" x2="50" y2="108"/>
  <line class="sw-drop" x1="142" y1="98" x2="142" y2="112"/>
  <text class="sw-flash" x="160" y="112">&#9889;</text>
</svg>
"""


# ---------------------------------------------------------------------------
# 狀態 / 組件
# ---------------------------------------------------------------------------


def _init_state(config: Dict[str, Any]) -> None:
    """初始化會話狀態；語言預設繁中，首屏為 landing。"""
    preset = config["presets"]["family_of_3"]
    defaults: Dict[str, Any] = {
        "lang": "zh-TW",
        "entered": False,
        "view": "location",
        "city": config["meta"]["default_city"],
        "month": 1,
        "people": preset["usage"]["people"],
        "shower_minutes_per_day": preset["usage"]["shower_minutes_per_day"],
        "laundry_loads_per_week": preset["usage"]["laundry_loads_per_week"],
        "dishwashing_habit": preset["usage"]["dishwashing_habit"],
        "drinking_cooking_liters_per_person_per_day": preset["usage"][
            "drinking_cooking_liters_per_person_per_day"
        ],
        "toilet_flushes_per_person_per_day": preset["usage"][
            "toilet_flushes_per_person_per_day"
        ],
        "target_savings": preset["target_savings"],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _set_view(view_key: str) -> None:
    st.session_state["view"] = view_key


def _set_month(month: int) -> None:
    st.session_state["month"] = month


def _set_language(language: str) -> None:
    st.session_state["lang"] = language


def _leave_app() -> None:
    st.session_state["entered"] = False


def _apply_preset(preset: Dict[str, Any]) -> None:
    for key, value in preset["usage"].items():
        st.session_state[key] = value
    st.session_state["target_savings"] = preset["target_savings"]


def _top_bar(lang: str, brand: bool = True) -> None:
    """頂部品牌 + 右上角語言切換（按鈕保持單行）。"""
    if brand:
        left, tw, en = st.columns([7, 1, 1])
        with left:
            st.markdown(
                '<div class="sw-topbar"><div class="sw-brand">'
                '<span>◈</span> SmartWater Optimizer'
                "</div></div>",
                unsafe_allow_html=True,
            )
    else:
        _, tw, en = st.columns([8, 1, 1])
    with tw:
        st.button(
            LANGUAGES["zh-TW"],
            type="primary" if lang == "zh-TW" else "secondary",
            use_container_width=True,
            key="lang_tw",
            on_click=_set_language,
            args=("zh-TW",),
        )
    with en:
        st.button(
            LANGUAGES["en"],
            type="primary" if lang == "en" else "secondary",
            use_container_width=True,
            key="lang_en",
            on_click=_set_language,
            args=("en",),
        )


def _render_landing(lang: str) -> None:
    """渲染安靜的lander，點擊按鈕後才進入主應用。"""
    st.markdown(
        f"""
<div class="sw-landing">
  <div class="sw-landing-kicker">{t('landing_kicker', lang)}</div>
  <h1>{t('landing_pre', lang)}<em>{t('landing_em', lang)}</em></h1>
  <p>{t('landing_desc', lang)}</p>
  <a class="sw-enter" href="?{_state_query({'enter': '1'})}" target="_self">{t('landing_enter', lang)}</a>
</div>
""",
        unsafe_allow_html=True,
    )


def _console(view: str, lang: str) -> None:
    """左上角三步驟控制台，點擊切換頁面。"""
    st.markdown(
        f'<div class="sw-console"><div class="sw-console-label">'
        f"{'操作流程' if lang == 'zh-TW' else 'WORKFLOW'}"
        f"</div></div>",
        unsafe_allow_html=True,
    )
    keys = [
        ("location", "console_location"),
        ("lifestyle", "console_lifestyle"),
        ("result", "console_result"),
    ]
    left, _, _, _ = st.columns([3.4, 1, 1, 1])
    with left:
        cols = st.columns(3)
        for idx, (view_key, label_key) in enumerate(keys):
            with cols[idx]:
                st.button(
                    t(label_key, lang),
                    type="primary" if view == view_key else "secondary",
                    use_container_width=True,
                    key=f"console_{view_key}",
                    on_click=_set_view,
                    args=(view_key,),
                )


def _rain_level(rainfall: float) -> str:
    """按降水量劃分小雨 / 中雨 / 大雨動畫等級。"""
    if rainfall < 40.0:
        return "light"
    if rainfall < 120.0:
        return "moderate"
    return "heavy"


def _state_query(extra: Dict[str, str] | None = None) -> str:
    """把目前狀態序列化為 URL 查詢字串，供整頁重載後還原。"""
    params: Dict[str, str] = {}
    for key in STATE_KEYS:
        value = st.session_state.get(key)
        if key == "entered":
            params["enter"] = "1" if value else "0"
        elif value is not None:
            params[key] = str(value)
    if extra:
        params.update(extra)
    return urlencode(params)


def _restore_state_from_query() -> bool:
    """若網址帶有狀態參數則還原，回傳是否發生還原。

    所有取值在寫入 session_state 前都會校驗合法性，
    非法值（如未知城市、越界月份）會被靜默忽略，避免後續 KeyError。
    """
    query = st.query_params
    if not query:
        return False
    cfg = load_config()
    cities_cfg = cfg["cities"]
    selectable_cities = {
        key for key in cities_cfg if key in cfg["tariffs"]
    }
    habits_cfg = cfg["usage_rates"]["dishwashing"]
    changed = False
    if "enter" in query:
        st.session_state["entered"] = query["enter"] == "1"
        changed = True
    for key in STATE_KEYS:
        if key == "entered" or key not in query:
            continue
        raw = query[key]
        try:
            if key in INT_KEYS:
                # 严格要求整数语法：int("1.9") 抛出 ValueError，
                # 由外层捕获后静默忽略，而不是把 1.9 截断成 1。
                value: Any = int(raw)
            elif key in FLOAT_KEYS:
                value = float(raw)
            else:
                value = str(raw)
        except (TypeError, ValueError):
            continue
        if key == "city" and value not in selectable_cities:
            continue
        if key == "view" and value not in VIEWS:
            continue
        if key == "lang" and value not in ("zh-TW", "en"):
            continue
        if key == "dishwashing_habit" and value not in habits_cfg:
            continue
        if key == "month" and not 1 <= value <= 12:
            continue
        if key == "people" and value < 1:
            continue
        if key in FLOAT_KEYS and value < 0:
            continue
        st.session_state[key] = value
        changed = True
    return changed


def _month_selector(rainfall: List[float], selected: int, lang: str) -> None:
    """渲染 12 個原生 Streamlit 月份按鈕，懸停顯示對應雨勢動畫。

    點擊按鈕透過 callback 更新 ``session_state``，由 Streamlit 自動重跑，
    不會產生新的瀏覽器頁面或整頁重載。
    """
    columns = st.columns(12)
    for month, column in zip(range(1, 13), columns):
        value = rainfall[month - 1]
        level = _rain_level(value)
        active = " active" if month == selected else ""
        align = " align-left" if month <= 2 else (" align-right" if month >= 11 else "")
        label = f"{month}{t('month_unit', lang)}"
        with column:
            st.button(
                label,
                key=f"month_{month}",
                use_container_width=True,
                on_click=_set_month,
                args=(month,),
            )
            st.markdown(
                f'<div class="sw-month-rain{active}">{value:.0f} mm</div>'
                f'<div class="sw-tip {level}{align}">'
                f'<div class="sw-tip-head">{label} · {value:.0f} mm · '
                f"{t('rain_' + level, lang)}</div>"
                f'<div class="sw-rain-scene">{RAIN_SVG}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )


def _render_map(city_data: Dict[str, Any], city_label: str, lang: str) -> None:
    """Render an interactive map centred on the selected city."""
    latitude = float(city_data["latitude"])
    longitude = float(city_data["longitude"])
    fmap = folium.Map(
        location=[latitude, longitude],
        zoom_start=10,
        tiles="OpenStreetMap",
    )
    folium.Marker(
        location=[latitude, longitude],
        tooltip=city_label,
        popup=city_label,
        icon=folium.Icon(color="green", icon="tint", prefix="fa"),
    ).add_to(fmap)
    folium.CircleMarker(
        location=[latitude, longitude],
        radius=28,
        color="#0a5c4a",
        fill=True,
        fill_color="#0a5c4a",
        fill_opacity=0.16,
    ).add_to(fmap)
    st_component_html(fmap.get_root().render(), height=300, scrolling=False)
    st.caption(t("map_caption", lang))


def _donut_html(categories: Dict[str, Dict[str, Any]], lang: str) -> str:
    """生成純 CSS 環形圖與圖例。"""
    keys = list(categories)
    total = sum(categories[key]["share_pct"] for key in keys) or 1.0
    stops: List[str] = []
    cursor = 0.0
    for key, color in zip(keys, DONUT_COLORS):
        end = cursor + categories[key]["share_pct"] / total * 100.0
        stops.append(f"{color} {cursor:.2f}% {end:.2f}%")
        cursor = end
    top_key = max(keys, key=lambda key: categories[key]["share_pct"])
    top = categories[top_key]
    legend = "".join(
        f'<div class="sw-legend-row"><span class="sw-dot" style="background:{color}"></span>'
        f"<span>{localized(categories[key]['label_zh'], categories[key]['label_en'], lang)}</span>"
        f"<b>{categories[key]['share_pct']:.1f}%</b></div>"
        for key, color in zip(keys, DONUT_COLORS)
    )
    top_label = "頭號費水" if lang == "zh-TW" else "Top use"
    return f"""
<div class="sw-donut-wrap">
  <div class="sw-donut" style="background: conic-gradient({', '.join(stops)})">
    <div class="sw-donut-hole"><span>{top_label}</span>
      <strong>{localized(top['label_zh'], top['label_en'], lang)}</strong>
      <span>{top['share_pct']:.1f}%</span></div>
  </div>
  <div class="sw-legend">{legend}</div>
</div>
"""


def _action_rows_html(plan: Dict[str, Any], symbol: str, lang: str) -> str:
    """生成按舒適度折損排序的行動清單。"""
    rows: List[str] = []
    for measure in plan["selected_measures"]:
        score = measure["comfort_penalty_score"]
        level = "low" if score <= 1 else ("mid" if score <= 2 else "high")
        rows.append(
            f"""
<div class="sw-action">
  <div>
    <div class="sw-action-title">{localized(measure['description_zh'], measure['description_en'], lang)}</div>
    <div class="sw-action-sub">{measure['description_en'] if lang == 'en' else to_traditional(measure['description_zh'])}</div>
  </div>
  <div class="sw-action-stat"><span>{t('saved_day', lang)}</span>
    <strong>{measure['water_saved_liters_per_day']:.0f} L</strong></div>
  <div class="sw-action-stat"><span>{t('saved_cycle', lang)}</span>
    <strong>{symbol}{measure['savings']:.2f}</strong></div>
  <div class="sw-badge {level}">{t('comfort_cost', lang, n=score)}</div>
</div>
"""
        )
    return "".join(rows)


def _section(title: str) -> None:
    """渲染帶下劃線的區塊標題。"""
    st.markdown(
        f'<div class="sw-section"><h2>{title}</h2></div>',
        unsafe_allow_html=True,
    )


def _alert(level: str, message: str) -> None:
    """渲染高對比度提示橫幅。"""
    st.markdown(
        f'<div class="sw-alert {level}">{message}</div>',
        unsafe_allow_html=True,
    )


def _next_button(label_key: str, lang: str, target: str) -> None:
    """渲染前往下一步的按鈕。"""
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.button(
            t(label_key, lang),
            type="primary",
            use_container_width=True,
            on_click=_set_view,
            args=(target,),
        )


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def main() -> None:
    """Streamlit 應用主流程。"""
    config = load_config()
    _init_state(config)

    if _restore_state_from_query():
        st.query_params.clear()
        st.rerun()

    lang: str = st.session_state["lang"]
    st.markdown(CSS, unsafe_allow_html=True)
    _top_bar(lang)

    if not st.session_state["entered"]:
        _render_landing(lang)
        return

    view: str = st.session_state["view"]
    _console(view, lang)

    st.button(
        "← " + t("back", lang),
        on_click=_leave_app,
    )

    cities: Dict[str, Any] = config["cities"]
    presets: Dict[str, Any] = config["presets"]
    habits: Dict[str, Any] = config["usage_rates"]["dishwashing"]

    city_key: str = st.session_state["city"]
    month: int = st.session_state["month"]
    city_data = cities[city_key]
    city_label = localized(city_data["name_zh"], city_data["name_en"], lang)
    tariff_key: str = city_data["tariff_key"]
    tariff = config["tariffs"][tariff_key]
    tariff_name = localized(tariff["name_zh"], tariff["name_en"], lang)
    symbol = CURRENCY_SYMBOLS.get(tariff["currency"], tariff["currency"] + " ")
    status = check_drought_status(city_key, month)

    if view == "location":
        _section(t("city_label", lang))
        selectable_cities = [
            key for key in cities if key in config["tariffs"]
        ]
        st.selectbox(
            t("city_label", lang),
            options=selectable_cities,
            format_func=lambda key: localized(
                cities[key]["name_zh"], cities[key]["name_en"], lang
            ),
            key="city",
        )
        st.caption(
            t(
                "tariff_caption",
                lang,
                name=tariff_name,
                months=tariff["billing_cycle_months"],
            )
        )
        rain_col, line_col, _ = st.columns(3)
        rain_col.metric(
            t("month_label", lang) + " · mm",
            f"{status['rainfall_mm']:.0f}",
        )
        line_col.metric(
            "警戒線" if lang == "zh-TW" else "Alert line",
            f"{status['drought_threshold_mm']:.0f}",
        )
        _section(t("month_label", lang))
        _month_selector(city_data["monthly_rainfall_mm"], month, lang)
        st.caption(t("month_hint", lang))
        _section(t("map_title", lang))
        _render_map(city_data, city_label, lang)
        alert_text = (
            status["message_en"]
            if lang == "en"
            else to_traditional(status["message_zh"])
        )
        _alert(
            {"critical": "crit", "warning": "warn", "normal": "ok"}[
                status["alert_level"]
            ],
            alert_text,
        )
        _next_button("next_lifestyle", lang, "lifestyle")
        return

    if view == "lifestyle":
        _section(t("preset_title", lang))
        st.caption(t("lifestyle_hint", lang))
        preset_items = list(presets.items())
        for row in range(0, len(preset_items), 4):
            cols = st.columns(4)
            for idx, (_, preset) in enumerate(preset_items[row : row + 4]):
                with cols[idx]:
                    st.button(
                        localized(preset["label_zh"], preset["label_en"], lang),
                        use_container_width=True,
                        on_click=_apply_preset,
                        args=(preset,),
                    )
        _section(t("params_title", lang))
        p1, p2 = st.columns(2)
        with p1:
            st.slider(t("people", lang), 1, 8, key="people")
            st.slider(
                t("shower", lang), 0.0, 30.0, step=0.5, key="shower_minutes_per_day"
            )
        with p2:
            st.slider(
                t("laundry", lang), 0.0, 14.0, step=1.0, key="laundry_loads_per_week"
            )
            st.selectbox(
                t("dish", lang),
                options=list(habits),
                format_func=lambda key: localized(
                    habits[key]["label_zh"], habits[key]["label_en"], lang
                ),
                key="dishwashing_habit",
            )
        st.slider(
            t("target", lang, currency=tariff["currency"]),
            0.0,
            200.0,
            step=5.0,
            key="target_savings",
        )
        _next_button("next_result", lang, "result")
        return

    # view == "result"
    usage_params = {
        key: st.session_state[key]
        for key in (
            "people",
            "shower_minutes_per_day",
            "laundry_loads_per_week",
            "dishwashing_habit",
            "drinking_cooking_liters_per_person_per_day",
            "toilet_flushes_per_person_per_day",
        )
    }
    breakdown = analyze_usage_breakdown(usage_params)
    total_m3: float = breakdown["total_m3"]
    bill = calculate_tiered_bill(total_m3, tariff["brackets"])
    cycle_months: int = int(tariff["billing_cycle_months"])
    # 引擎以完整帳單週期計算，介面統一換算為「每月」顯示。
    monthly_target = float(st.session_state["target_savings"])
    plan = generate_conservation_plan(
        total_m3,
        monthly_target * cycle_months,
        status["is_drought"],
        tariff_key,
        usage_categories={
            key: item["daily_liters"]
            for key, item in breakdown["categories"].items()
        },
    )
    monthly_bill = bill["total_bill"] / cycle_months
    monthly_savings = plan["projected_savings"] / cycle_months
    monthly_bill_after = plan["projected_bill"] / cycle_months
    monthly_shortfall = plan["shortfall"] / cycle_months

    _section(t("overview", lang))
    m1, m2, m3 = st.columns(3)
    m1.metric(
        t("total_bill", lang),
        f"{symbol}{monthly_bill:,.2f}",
    )
    m2.metric(t("tier", lang), t("tier_value", lang, n=bill["current_tier"]))
    m3.metric(t("savings", lang), f"{symbol}{monthly_savings:,.2f}")

    if bill["m3_to_next_tier"] is None:
        st.caption(t("top_tier", lang))
    else:
        st.caption(
            t(
                "next_tier",
                lang,
                n=bill["current_tier"] + 1,
                m3=bill["m3_to_next_tier"],
                total=total_m3,
                liters=breakdown["daily_total_liters"],
            )
        )

    _section(t("breakdown", lang))
    chart_col, donut_col = st.columns([3, 2])
    with chart_col:
        chart_data = pd.DataFrame(
            {
                t("volume_col", lang): {
                    localized(
                        item["label_zh"], item["label_en"], lang
                    ): item["cycle_m3"] / cycle_months
                    for item in breakdown["categories"].values()
                }
            }
        )
        st.bar_chart(chart_data, color="#0a5c4a")
        st.caption(
            t(
                "villain",
                lang,
                name=localized(
                    breakdown["top_consumer_label_zh"],
                    breakdown["top_consumer_label_en"],
                    lang,
                ),
                pct=breakdown["top_consumer_share_pct"],
            )
        )
    with donut_col:
        st.markdown(_donut_html(breakdown["categories"], lang), unsafe_allow_html=True)

    if status["is_drought"]:
        quota_total = status["safe_daily_quota_l_per_person"] * usage_params["people"]
        _alert(
            "info",
            t("drought_note", lang, quota=quota_total, usage=breakdown["daily_total_liters"]),
        )

    _section(t("actions", lang))
    if plan["selected_measures"]:
        st.markdown(_action_rows_html(plan, symbol, lang), unsafe_allow_html=True)
    else:
        _alert("info", t("no_action", lang))

    tc, wc = st.columns(2)
    tc.metric(t("total_comfort", lang), f"{plan['total_comfort_penalty']}")
    saved_label = (
        f"{plan['water_saved_liters_per_day']:.0f} L/日"
        if lang == "zh-TW"
        else f"{plan['water_saved_liters_per_day']:.0f} L/day"
    )
    wc.metric(t("water_saved", lang), saved_label)

    if plan["target_achievable"]:
        _alert(
            "ok",
            t(
                "goal_met",
                lang,
                symbol=symbol,
                actual=monthly_savings,
                target=monthly_target,
                bill=monthly_bill_after,
            ),
        )
    else:
        _alert(
            "warn",
            t(
                "goal_missed",
                lang,
                symbol=symbol,
                actual=monthly_savings,
                gap=monthly_shortfall,
            ),
        )

    st.caption(localized(config["meta"]["note_zh"], config["meta"]["note_en"], lang))
    st.caption(t("source_note", lang))


if __name__ == "__main__":
    main()
