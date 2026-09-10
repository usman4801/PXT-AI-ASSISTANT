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
RESET_DELAY = 12

BANNER_1_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner.mp4"
BANNER_2_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner2.mp4"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# SAFE SESSION STATE INITIALIZATION
# ============================================================
st.session_state.setdefault("active_banner", 1)
st.session_state.setdefault("kiosk_state", "idle")
st.session_state.setdefault("current_employee", None)
st.session_state.setdefault("last_heard", "")
st.session_state.setdefault("last_interaction", None)

# Handle Banner Switch from Dot
if "switch_banner" in st.query_params:
    st.session_state.active_banner = 2 if st.session_state.active_banner == 1 else 1
    del st.query_params["switch_banner"]
    st.rerun()


# ============================================================
# CSS & STYLING
# ============================================================
active_video = BANNER_1_URL if st.session_state.active_banner == 1 else BANNER_2_URL

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
        }

        /* PXT HUB Title */
        .hud-title-wrap {
            position: fixed;
            top: 14vh;
            left: 50%;
            transform: translateX(-50%);
            z-index: 30;
            text-align: center;
            pointer-events: none;
        }

        .hud-pxt-title {
            font-size: 1.35rem !important;
            font-weight: 800;
            letter-spacing: 0.22em;
            color: #ffffff;
            text-shadow: 0 0 12px rgba(56, 189, 248, 0.9), 0 0 25px rgba(56, 189, 248, 0.5);
            text-transform: uppercase;
        }

        /* Gale / Neck ke paas small gray text */
        .throat-prompt {
            position: fixed;
            top: 32vh;
            left: 50%;
            transform: translateX(-50%);
            z-index: 35;
            color: #94a3b8;
            font-size: 0.72rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            font-weight: 500;
            pointer-events: none;
            background: rgba(15, 23, 42, 0.5);
            padding: 2px 10px;
            border-radius: 999px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        /* Top HUD Bar */
        .top-hud-bar {
            position: fixed;
            top: 16px;
            left: 0;
            width: 100vw;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 22px;
            z-index: 50;
            box-sizing: border-box;
            pointer-events: none;
        }

        .mic-dot-container {
            display: flex;
            align-items: center;
            gap: 7px;
        }

        .red-mic-dot {
            width: 8px;
            height: 8px;
            background: #ef4444;
            border-radius: 50%;
            box-shadow: 0 0 8px #ef4444;
        }

        .green-mic-dot {
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            box-shadow: 0 0 10px #22c55e, 0 0 18px #22c55e;
            animation: pulseGreen 1.2s infinite ease-in-out;
        }

        @keyframes pulseGreen {
            0%, 100% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.4); opacity: 1; }
        }

        .mic-label-red {
            color: #f87171;
            font-weight: 600;
            font-size: 0.65rem !important;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .mic-label-green {
            color: #4ade80;
            font-weight: 600;
            font-size: 0.65rem !important;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .heard-capsule {
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(56, 189, 248, 0.4);
            padding: 4px 14px;
            border-radius: 999px;
            color: #bae6fd;
            font-size: 0.8rem;
            backdrop-filter: blur(12px);
            max-width: 380px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.25);
        }

        /* Top Right Theme Dot */
        .theme-dot-anchor {
            position: fixed;
            top: 18px;
            right: 22px;
            width: 14px;
            height: 14px;
            background: #38bdf8;
            border: 1.5px solid #ffffff;
            border-radius: 50%;
            box-shadow: 0 0 10px #38bdf8, 0 0 18px rgba(56, 189, 248, 0.8);
            z-index: 99999;
            cursor: pointer;
            text-decoration: none;
            display: block;
        }

        /* Bottom Floating Deck */
        .kiosk-bottom-deck {
            position: fixed;
            bottom: 3.5vh;
            left: 50%;
            transform: translateX(-50%);
            z-index: 50;
            width: 88%;
            max-width: 480px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
        }

        .employee-glass-card {
            background: rgba(11, 15, 25, 0.85);
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border: 1.5px solid rgba(56, 189, 248, 0.4);
            border-radius: 18px;
            padding: 1.1rem 1.4rem;
            width: 100%;
            text-align: center;
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.8), 0 0 25px rgba(56, 189, 248, 0.25);
            animation: slideUp 0.3s ease-out;
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(15px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .emp-name {
            font-size: 1.4rem;
            font-weight: 800;
            color: #ffffff;
        }
        .emp-badge {
            color: #38bdf8;
            font-size: 0.85rem;
            margin-bottom: 0.7rem;
        }
        .emp-stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
        }
        .emp-stat-box {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 0.5rem 0.2rem;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .emp-stat-lbl {
            font-size: 0.62rem;
            color: #94a3b8;
            text-transform: uppercase;
        }
        .emp-stat-val {
            font-size: 1.05rem;
            font-weight: 700;
            margin-top: 2px;
        }
        .status-present { color: #34d399; }
        .status-leave { color: #fb923c; }

        div[data-testid="stTextInput"] { width: 100% !important; }
        div[data-testid="stTextInput"] input {
            background: rgba(15, 23, 42, 0.9) !important;
            border: 1.5px solid rgba(56, 189, 248, 0.45) !important;
            border-radius: 14px !important;
            color: #ffffff !important;
            height: 3rem;
            font-size: 0.98rem !important;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.6);
        }

        .kiosk-bottom-deck .stButton > button {
            background: rgba(15, 23, 42, 0.88) !important;
            border: 1.5px solid rgba(56, 189, 248, 0.4) !important;
            border-radius: 999px !important;
            color: #ffffff !important;
            height: 2.7rem !important;
            padding: 0 1.4rem !important;
            font-size: 0.9rem !important;
            font-weight: 600;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Background Video & PXT HUB Title
st.markdown(
    f"""
    <video id="kiosk-bg-video" autoplay loop muted playsinline key="{active_video}">
        <source src="{active_video}" type="video/mp4">
    </video>
    <div class="hud-title-wrap">
        <div class="hud-pxt-title">{APP_TITLE}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Gale ke paas subtle text (sirf idle state mein)
if st.session_state.get("kiosk_state") == "idle":
    st.markdown('<div class="throat-prompt">Say "Hi PXT"</div>', unsafe_allow_html=True)

# Top Right Theme Dot Link
st.markdown(
    """<a href="?switch_banner=true" target="_self" class="theme-dot-anchor" title="Switch Theme"></a>""",
    unsafe_allow_html=True,
)

# Top HUD Bar (Mic Indicator: Red default, Green jab koi awaz capture ho)
last_heard_text = st.session_state.get("last_heard", "").strip()

if last_heard_text:
    dot_class = "green-mic-dot"
    label_class = "mic-label-green"
    label_text = "LISTENING..."
    heard_pill = f'<div class="heard-capsule">Heard: {last_heard_text}</div>'
else:
    dot_class = "red-mic-dot"
    label_class = "mic-label-red"
    label_text = "MIC ON"
    heard_pill = ""

st.markdown(
    f"""
    <div class="top-hud-bar">
        <div class="mic-dot-container">
            <span class="{dot_class}"></span>
            <span class="{label_class}">{label_text}</span>
        </div>
        {heard_pill}
        <div style="width: 20px;"></div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA & SPEECH ENGINE
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
    else:
        return f"{name}, your status is {emp['Status']}, remaining leaves are {emp['RemainingLeaves']}, and next off is {emp['NextOffDay']}."


# Safe Auto Reset
last_act = st.session_state.get("last_interaction", None)
if last_act and (time.time() - last_act > RESET_DELAY):
    st.session_state["kiosk_state"] = "idle"
    st.session_state["current_employee"] = None
    st.session_state["last_interaction"] = None
    st.session_state["last_heard"] = ""
    st.rerun()

staff_df = load_data()


# ============================================================
# KIOSK INTERACTION DECK
# ============================================================
st.markdown('<div class="kiosk-bottom-deck">', unsafe_allow_html=True)

# 1. IDLE STATE
if st.session_state.get("kiosk_state") == "idle":
    spoken = None
    if MIC_AVAILABLE:
        spoken = speech_to_text(
            language="en-US",
            start_prompt="🎙️ Say 'Hi PXT' or Tap Here",
            stop_prompt="⏹️ Listening...",
            just_once=True,
            key="idle_mic_btn",
        )
    else:
        if st.button("🎙️ Say 'Hi PXT' or Tap Here"):
            spoken = "Hi PXT"

    if spoken:
        st.session_state["last_heard"] = spoken
        st.session_state["kiosk_state"] = "asked_badge"
        st.session_state["last_interaction"] = time.time()
        speak("Hello! Please enter your Badge Number.")
        st.rerun()

# 2. ASKED BADGE STATE
elif st.session_state.get("kiosk_state") == "asked_badge":
    badge_in = st.text_input(
        "badge_in",
        placeholder="Enter Badge No (e.g. EMP011)",
        label_visibility="collapsed",
        key="badge_input_field",
    )

    badge_voice = None
    if MIC_AVAILABLE:
        badge_voice = speech_to_text(
            language="en-US",
            start_prompt="🎙️ Speak Badge No",
            stop_prompt="⏹️",
            just_once=True,
            key="badge_voice_btn",
        )

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
            welcome_msg = f"Welcome {match.iloc[0]['Name']}. How can I help you?"
            speak(welcome_msg)
            st.rerun()
        else:
            st.error("Badge Number not found. Try again.")

# 3. EMPLOYEE ACTIVE STATE
elif st.session_state.get("kiosk_state") == "employee_active":
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
                    <div class="emp-stat-lbl">LEAVES LEFT</div>
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

    q_col1, q_col2 = st.columns([4, 1])
    with q_col1:
        question_text = st.text_input(
            "ask_box",
            placeholder="Ask: 'Leaves left?' or 'Next off?'",
            label_visibility="collapsed",
            key="ask_question_input",
        )
    with q_col2:
        question_voice = None
        if MIC_AVAILABLE:
            question_voice = speech_to_text(
                language="en-US",
                start_prompt="🎙️",
                stop_prompt="⏹️",
                just_once=True,
                key="qa_mic_btn",
            )

    active_question = question_voice if question_voice else question_text
    if active_question:
        st.session_state["last_heard"] = active_question
        st.session_state["last_interaction"] = time.time()
        ans = answer_employee_question(emp, active_question)
        speak(ans)

    components.html(
        f"""
        <script>
            setTimeout(function() {{
                window.parent.location.reload();
            }}, {int(RESET_DELAY * 1000)});
        </script>
        """,
        height=0,
    )

st.markdown('</div>', unsafe_allow_html=True)
