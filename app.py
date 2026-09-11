"""
PXT HUB - Clean Cyber Kiosk with Voice Recognition & Banner Switcher
"""

from __future__ import annotations

import io
import os
import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

try:
    from streamlit_mic_recorder import speech_to_text
    MIC_AVAILABLE = True
except ImportError:
    MIC_AVAILABLE = False


# ============================================================
# CONFIGURATION
# ============================================================
APP_TITLE = "PXT HUB"
DATA_FILE = "staff_data.csv"
RESET_DELAY = 15

BANNER_1_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner.mp4"
BANNER_2_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner2.mp4"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Safe Session State Initialization
st.session_state.setdefault("active_banner", 1)
st.session_state.setdefault("kiosk_state", "idle")
st.session_state.setdefault("current_employee", None)
st.session_state.setdefault("last_heard", "")
st.session_state.setdefault("last_interaction", None)

if "switch_banner" in st.query_params:
    st.session_state.active_banner = 2 if st.session_state.active_banner == 1 else 1
    del st.query_params["switch_banner"]
    st.rerun()

active_video = BANNER_1_URL if st.session_state.active_banner == 1 else BANNER_2_URL

# ============================================================
# CSS & STYLING
# ============================================================
st.markdown(
    """
    <style>
        #MainMenu, header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="collapsedControl"] {
            display: none !important;
            visibility: hidden !important;
        }

        html, body, [data-testid="stAppViewContainer"], .stApp {
            background: #000000 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            height: 100vh !important;
            width: 100vw !important;
        }

        .main .block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100vw !important;
            width: 100vw !important;
            height: 100vh !important;
        }

        #kiosk-bg-video {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            object-fit: cover;
            z-index: 1;
            pointer-events: none;
        }

        .hud-title-wrap {
            position: fixed;
            top: 10vh;
            left: 50%;
            transform: translateX(-50%);
            z-index: 30;
            text-align: center;
            pointer-events: none;
        }

        .hud-pxt-title {
            font-size: 1.5rem !important;
            font-weight: 800;
            letter-spacing: 0.25em;
            color: #ffffff;
            text-shadow: 0 0 15px rgba(56, 189, 248, 0.9), 0 0 25px rgba(56, 189, 248, 0.5);
            text-transform: uppercase;
        }

        .top-hud-bar {
            position: fixed;
            top: 16px;
            left: 0;
            width: 100vw;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 24px;
            z-index: 50;
            box-sizing: border-box;
            pointer-events: none;
        }

        .mic-dot-container {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .active-mic-dot {
            width: 10px;
            height: 10px;
            background: #22c55e;
            border-radius: 50%;
            box-shadow: 0 0 10px #22c55e;
            animation: pulse 1.2s infinite ease-in-out;
        }

        .idle-mic-dot {
            width: 10px;
            height: 10px;
            background: #38bdf8;
            border-radius: 50%;
            box-shadow: 0 0 8px #38bdf8;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.3); opacity: 1; }
        }

        .mic-label {
            color: #e2e8f0;
            font-weight: 600;
            font-size: 0.75rem !important;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .theme-dot-anchor {
            position: fixed;
            top: 18px;
            right: 22px;
            width: 16px;
            height: 16px;
            background: #38bdf8;
            border: 2px solid #ffffff;
            border-radius: 50%;
            box-shadow: 0 0 12px #38bdf8;
            z-index: 99999;
            cursor: pointer;
            display: block;
        }

        /* Interactive Deck centered at bottom */
        .kiosk-bottom-deck {
            position: fixed;
            bottom: 6vh;
            left: 50%;
            transform: translateX(-50%);
            z-index: 100;
            width: 90%;
            max-width: 440px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
            pointer-events: auto !important;
        }

        .kiosk-bottom-deck button {
            background: rgba(15, 23, 42, 0.85) !important;
            border: 1.5px solid #38bdf8 !important;
            color: #ffffff !important;
            border-radius: 30px !important;
            font-weight: 600 !important;
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.4) !important;
            padding: 8px 24px !important;
        }

        .employee-glass-card {
            background: rgba(11, 15, 25, 0.9);
            backdrop-filter: blur(25px);
            border: 1.5px solid rgba(56, 189, 248, 0.5);
            border-radius: 16px;
            padding: 1rem;
            width: 100%;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.8);
        }

        .emp-name { font-size: 1.3rem; font-weight: 700; color: #ffffff; }
        .emp-badge { color: #38bdf8; font-size: 0.85rem; margin-bottom: 8px; }
        .emp-stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
        .emp-stat-box { background: rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 6px; }
        .emp-stat-lbl { font-size: 0.6rem; color: #94a3b8; }
        .emp-stat-val { font-size: 1rem; font-weight: 700; margin-top: 2px; }
        .status-present { color: #34d399; }
        .status-leave { color: #fb923c; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Background Video & Header
st.markdown(
    f"""
    <video id="kiosk-bg-video" autoplay loop muted playsinline>
        <source src="{active_video}" type="video/mp4">
    </video>
    <div class="hud-title-wrap">
        <div class="hud-pxt-title">{APP_TITLE}</div>
    </div>
    <a href="?switch_banner=true" target="_self" class="theme-dot-anchor" title="Switch Banner"></a>
    """,
    unsafe_allow_html=True,
)

# Top Bar Indicator
last_heard_text = st.session_state.get("last_heard", "").strip()
dot_class = "active-mic-dot" if last_heard_text else "idle-mic-dot"
status_msg = f"HEARD: {last_heard_text}" if last_heard_text else "READY"

st.markdown(
    f"""
    <div class="top-hud-bar">
        <div class="mic-dot-container">
            <span class="{dot_class}"></span>
            <span class="mic-label">{status_msg}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# DATA & FUNCTIONS
# ============================================================
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            return pd.read_csv(DATA_FILE, dtype=str).fillna("")
        except Exception:
            pass
    return pd.DataFrame([
        {"EmployeeID": "EMP001", "Name": "Ayesha Khan", "Status": "Present", "RemainingLeaves": "12", "NextOffDay": "Saturday"},
        {"EmployeeID": "EMP002", "Name": "Bilal Ahmed", "Status": "On Leave", "RemainingLeaves": "5", "NextOffDay": "Sunday"},
        {"EmployeeID": "EMP011", "Name": "Usman", "Status": "Present", "RemainingLeaves": "20", "NextOffDay": "Friday"},
    ])

def speak(text: str):
    if not TTS_AVAILABLE:
        return
    try:
        buf = io.BytesIO()
        gTTS(text=text, lang="en").write_to_fp(buf)
        buf.seek(0)
        st.audio(buf, format="audio/mp3", autoplay=True)
    except Exception:
        pass

def answer_employee_question(emp, question: str) -> str:
    q = question.lower()
    name = emp['Name']
    if "leave" in q or "chutti" in q or "remaining" in q:
        return f"{name}, you have {emp['RemainingLeaves']} remaining leaves."
    elif "off" in q or "holiday" in q or "weekend" in q:
        return f"{name}, your next off day is on {emp['NextOffDay']}."
    elif "status" in q or "present" in q or "absent" in q:
        return f"{name}, your current status is {emp['Status']}."
    return f"{name}, status is {emp['Status']}, leaves left: {emp['RemainingLeaves']}, next off: {emp['NextOffDay']}."

staff_df = load_data()

# Auto Reset
last_act = st.session_state.get("last_interaction")
if last_act and (time.time() - last_act > RESET_DELAY):
    st.session_state["kiosk_state"] = "idle"
    st.session_state["current_employee"] = None
    st.session_state["last_interaction"] = None
    st.session_state["last_heard"] = ""
    st.rerun()

# ============================================================
# INTERACTION DECK
# ============================================================
st.markdown('<div class="kiosk-bottom-deck">', unsafe_allow_html=True)

state = st.session_state.get("kiosk_state", "idle")

if state == "idle":
    spoken = None
    if MIC_AVAILABLE:
        spoken = speech_to_text(
            language="en-US",
            start_prompt="🎙️ Tap to Speak / Say 'Hi'",
            stop_prompt="⏹️ Listening...",
            just_once=True,
            key="idle_mic_btn",
        )
    else:
        if st.button("🎙️ Tap to Wake Up"):
            spoken = "Hi PXT"

    if spoken:
        st.session_state["last_heard"] = spoken
        st.session_state["kiosk_state"] = "asked_badge"
        st.session_state["last_interaction"] = time.time()
        speak("Hello! Please state or type your Badge Number.")
        st.rerun()

elif state == "asked_badge":
    badge_voice = None
    if MIC_AVAILABLE:
        badge_voice = speech_to_text(
            language="en-US",
            start_prompt="🎙️ Speak Badge No",
            stop_prompt="⏹️ Processing...",
            just_once=True,
            key="badge_mic_btn",
        )

    badge_in = st.text_input("Badge Input", placeholder="Or type Badge No (e.g. EMP011)", label_visibility="collapsed")
    active_badge = badge_voice if badge_voice else badge_in

    if active_badge:
        st.session_state["last_heard"] = active_badge
        q = active_badge.strip().lower().replace(" ", "")
        match = staff_df[staff_df["EmployeeID"].str.lower().str.replace(" ", "") == q]
        if match.empty:
            match = staff_df[staff_df["Name"].str.lower().str.contains(active_badge.strip().lower())]

        if not match.empty:
            st.session_state["current_employee"] = match.iloc[0]
            st.session_state["kiosk_state"] = "employee_active"
            st.session_state["last_interaction"] = time.time()
            speak(f"Welcome {match.iloc[0]['Name']}. How can I assist you?")
            st.rerun()
        else:
            st.error("Badge Number not found. Try again.")

elif state == "employee_active":
    emp = st.session_state.get("current_employee")
    status_cls = "status-present" if "present" in emp["Status"].lower() else "status-leave"

    st.markdown(
        f"""
        <div class="employee-glass-card">
            <div class="emp-name">{emp['Name']}</div>
            <div class="emp-badge">BADGE ID: {emp['EmployeeID']}</div>
            <div class="emp-stats-grid">
                <div class="emp-stat-box">
                    <div class="emp-stat-lbl">STATUS</div>
                    <div class="emp-stat-val {status_cls}">{emp['Status']}</div>
                </div>
                <div class="emp-stat-box">
                    <div class="emp-stat-lbl">LEAVES</div>
                    <div class="emp-stat-val">{emp['RemainingLeaves']}</div>
                </div>
                <div class="emp-stat-box">
                    <div class="emp-stat-lbl">NEXT OFF</div>
                    <div class="emp-stat-val">{emp['NextOffDay']}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    q_voice = None
    if MIC_AVAILABLE:
        q_voice = speech_to_text(
            language="en-US",
            start_prompt="🎙️ Ask Question",
            stop_prompt="⏹️ Listening...",
            just_once=True,
            key="qa_mic_btn",
        )

    q_text = st.text_input("Ask", placeholder="Or type: Leaves left? / Next off?", label_visibility="collapsed")
    active_q = q_voice if q_voice else q_text

    if active_q:
        st.session_state["last_heard"] = active_q
        st.session_state["last_interaction"] = time.time()
        ans = answer_employee_question(emp, active_q)
        st.info(ans)
        speak(ans)

st.markdown('</div>', unsafe_allow_html=True)
