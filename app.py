"""
PXT HUB - Interactive Kiosk with Banner Switcher, Mic Dot & Voice Q&A
"""

from __future__ import annotations

import io
import os
import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Audio Dependencies
try:
    from streamlit_mic_recorder import speech_to_text
    MIC_AVAILABLE = True
except ImportError:
    MIC_AVAILABLE = False

try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False


# ============================================================
# CONFIGURATION
# ============================================================
DATA_FILE = "staff_data.csv"
RESET_DELAY = 12

# Dono Banners ke URLs
BANNER_1_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner.mp4"
BANNER_2_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner2.mp4"

st.set_page_config(
    page_title="PXT HUB",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# STATE INITIALIZATION
# ============================================================
if "active_banner" not in st.session_state:
    st.session_state.active_banner = 1  # 1 ya 2
if "kiosk_state" not in st.session_state:
    st.session_state.kiosk_state = "idle"  # idle -> asked_badge -> employee_active
if "current_employee" not in st.session_state:
    st.session_state.current_employee = None
if "last_heard" not in st.session_state:
    st.session_state.last_heard = ""
if "voice_feedback" not in st.session_state:
    st.session_state.voice_feedback = None
if "last_interaction" not in st.session_state:
    st.session_state.last_interaction = None


# ============================================================
# FULLSCREEN & HUD STYLING (MATCHING THE SCREENSHOT)
# ============================================================
active_video_url = BANNER_1_URL if st.session_state.active_banner == 1 else BANNER_2_URL

st.markdown(
    f"""
    <style>
        /* Hide all Streamlit extras */
        #MainMenu, header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="collapsedControl"] {{
            display: none !important;
            visibility: hidden !important;
        }}

        html, body, [data-testid="stAppViewContainer"], .stApp {{
            background: #000000 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            height: 100vh !important;
            width: 100vw !important;
        }}

        .main .block-container {{
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100vw !important;
            width: 100vw !important;
            height: 100vh !important;
        }}

        /* Edge-to-Edge Fullscreen Video */
        #kiosk-bg-video {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            object-fit: cover;
            z-index: 1;
        }}

        /* Center PXT HUB Title over Face/Nose area */
        .hud-title-wrap {{
            position: fixed;
            top: 18vh;
            left: 50%;
            transform: translateX(-50%);
            z-index: 20;
            text-align: center;
            pointer-events: none;
        }}

        .hud-pxt-title {{
            font-size: 2.8rem;
            font-weight: 900;
            letter-spacing: 0.28em;
            color: #ffffff;
            text-shadow: 0 0 15px rgba(56, 189, 248, 0.9), 0 0 35px rgba(56, 189, 248, 0.5), 0 0 60px rgba(14, 165, 233, 0.4);
            text-transform: uppercase;
        }}

        /* Top Bar Indicators (Left Mic, Center Heard, Right Banner Dot) */
        .top-hud-bar {{
            position: fixed;
            top: 20px;
            left: 0;
            width: 100vw;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 25px;
            z-index: 50;
            box-sizing: border-box;
            pointer-events: none;
        }}

        .mic-dot-container {{
            display: flex;
            align-items: center;
            gap: 10px;
            pointer-events: auto;
        }}

        .green-mic-dot {{
            width: 14px;
            height: 14px;
            background: #22c55e;
            border-radius: 50%;
            box-shadow: 0 0 15px #22c55e, 0 0 25px #22c55e;
            animation: pulseGreen 1.4s infinite ease-in-out;
        }}

        @keyframes pulseGreen {{
            0%, 100% {{ transform: scale(1); opacity: 0.8; }}
            50% {{ transform: scale(1.35); opacity: 1; }}
        }}

        .mic-label {{
            color: #4ade80;
            font-weight: 700;
            font-size: 0.82rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            text-shadow: 0 0 8px rgba(34, 197, 94, 0.6);
        }}

        /* Center Heard Capsule */
        .heard-capsule {{
            background: rgba(15, 23, 42, 0.75);
            border: 1px solid rgba(56, 189, 248, 0.4);
            padding: 6px 18px;
            border-radius: 999px;
            color: #bae6fd;
            font-size: 0.9rem;
            backdrop-filter: blur(15px);
            max-width: 480px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.25);
        }}

        /* Floating Interactive Bottom Area */
        .kiosk-bottom-deck {{
            position: fixed;
            bottom: 4vh;
            left: 50%;
            transform: translateX(-50%);
            z-index: 40;
            width: 90%;
            max-width: 580px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }}

        /* Employee Info Card */
        .employee-glass-card {{
            background: rgba(11, 15, 25, 0.82);
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border: 1.5px solid rgba(56, 189, 248, 0.45);
            border-radius: 20px;
            padding: 1.2rem 1.8rem;
            width: 100%;
            text-align: center;
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.8), 0 0 25px rgba(56, 189, 248, 0.25);
            animation: slideUp 0.3s ease-out;
        }}

        @keyframes slideUp {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .emp-name {{
            font-size: 1.6rem;
            font-weight: 800;
            color: #ffffff;
        }}
        .emp-badge {{
            color: #38bdf8;
            font-size: 0.9rem;
            letter-spacing: 0.08em;
            margin-bottom: 0.8rem;
        }}
        .emp-stats-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }}
        .emp-stat-box {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 0.6rem 0.3rem;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .emp-stat-lbl {{
            font-size: 0.65rem;
            color: #94a3b8;
            text-transform: uppercase;
        }}
        .emp-stat-val {{
            font-size: 1.1rem;
            font-weight: 700;
            margin-top: 3px;
        }}
        .status-present {{ color: #34d399; }}
        .status-leave {{ color: #fb923c; }}

        /* Input Controls */
        div[data-testid="stTextInput"] {{ width: 100% !important; }}
        div[data-testid="stTextInput"] input {{
            background: rgba(15, 23, 42, 0.9) !important;
            border: 1.5px solid rgba(56, 189, 248, 0.5) !important;
            border-radius: 14px !important;
            color: #ffffff !important;
            height: 3.2rem;
            font-size: 1.05rem !important;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.6);
        }}

        /* Buttons */
        .stButton > button {{
            background: rgba(15, 23, 42, 0.9) !important;
            border: 1.5px solid rgba(56, 189, 248, 0.5) !important;
            border-radius: 999px !important;
            color: #ffffff !important;
            height: 2.9rem !important;
            padding: 0 1.6rem !important;
            font-weight: 700;
            box-shadow: 0 4px 20px rgba(0,0,0,0.6);
        }}
        .stButton > button:hover {{
            border-color: #38bdf8 !important;
            color: #38bdf8 !important;
        }}

        /* Banner Switcher Button Top Right */
        .banner-btn-wrap {{
            position: fixed;
            top: 15px;
            right: 25px;
            z-index: 100;
        }}
        .banner-btn-wrap .stButton > button {{
            width: 22px !important;
            height: 22px !important;
            min-height: 22px !important;
            border-radius: 50% !important;
            background: #38bdf8 !important;
            border: none !important;
            box-shadow: 0 0 15px #38bdf8, 0 0 25px #0284c7 !important;
            padding: 0 !important;
            cursor: pointer;
        }}
    </style>

    <video id="kiosk-bg-video" autoplay loop muted playsinline key="{active_video_url}">
        <source src="{active_video_url}" type="video/mp4">
    </video>

    <div class="hud-title-wrap">
        <div class="hud-pxt-title">{APP_TITLE}</div>
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


# Auto Reset check (reset if idle for 12 seconds after result)
if st.session_state.last_interaction and (time.time() - st.session_state.last_interaction > RESET_DELAY):
    st.session_state.kiosk_state = "idle"
    st.session_state.current_employee = None
    st.session_state.last_interaction = None
    st.session_state.last_heard = ""
    st.rerun()

staff_df = load_data()


# ============================================================
# TOP HUD BAR (MIC DOT, HEARD TEXT, BANNER TOGGLE)
# ============================================================
heard_display = f"Heard: {st.session_state.last_heard}" if st.session_state.last_heard else "Heard: Waiting for voice..."

st.markdown(
    f"""
    <div class="top-hud-bar">
        <div class="mic-dot-container">
            <span class="green-mic-dot"></span>
            <span class="mic-label">MIC ON</span>
        </div>
        <div class="heard-capsule">{heard_display}</div>
        <div style="width: 30px;"></div>
    </div>
    """,
    unsafe_allow_html=True
)

# Top Right Banner Switch Dot
st.markdown('<div class="banner-btn-wrap">', unsafe_allow_html=True)
if st.button(" ", key="toggle_banner_dot", help="Switch Banner 1 / Banner 2"):
    st.session_state.active_banner = 2 if st.session_state.active_banner == 1 else 1
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# KIOSK CONVERSATION & Q/A LOGIC
# ============================================================
st.markdown('<div class="kiosk-bottom-deck">', unsafe_allow_html=True)

# 1. IDLE STATE: Waiting for "Hi PXT"
if st.session_state.kiosk_state == "idle":
    if MIC_AVAILABLE:
        spoken = speech_to_text(
            language="en-US",
            start_prompt="🎙️ Say 'Hi PXT' to Start",
            stop_prompt="⏹️ Listening...",
            just_once=True,
            key="idle_mic_btn",
        )
        if spoken:
            st.session_state.last_heard = spoken
            if "pxt" in spoken.lower() or "hi" in spoken.lower():
                st.session_state.kiosk_state = "asked_badge"
                speak("Hello! Please say or enter your Badge Number.")
                st.rerun()
    else:
        if st.button("🎙️ Wake Up (Hi PXT)"):
            st.session_state.last_heard = "Hi PXT"
            st.session_state.kiosk_state = "asked_badge"
            speak("Hello! Please enter your Badge Number.")
            st.rerun()

# 2. ASKED BADGE STATE: User enters or speaks Badge Number
elif st.session_state.kiosk_state == "asked_badge":
    badge_in = st.text_input(
        "badge_in",
        placeholder="Say or Type Badge No (e.g. EMP011)",
        label_visibility="collapsed",
        key="badge_input_field",
    )

    if MIC_AVAILABLE:
        badge_voice = speech_to_text(
            language="en-US",
            start_prompt="🎙️ Speak Badge Number",
            stop_prompt="⏹️ Done",
            just_once=True,
            key="badge_voice_btn",
        )
        if badge_voice:
            badge_in = badge_voice
            st.session_state.last_heard = badge_voice

    if badge_in:
        st.session_state.last_heard = badge_in
        q = badge_in.strip().lower().replace(" ", "")
        match = staff_df[staff_df["EmployeeID"].str.lower().str.replace(" ", "") == q]
        if match.empty:
            match = staff_df[staff_df["Name"].str.lower().str.contains(badge_in.strip().lower())]

        if not match.empty:
            st.session_state.current_employee = match.iloc[0]
            st.session_state.kiosk_state = "employee_active"
            st.session_state.last_interaction = time.time()
            welcome_msg = f"Welcome {match.iloc[0]['Name']}. How can I help you today?"
            speak(welcome_msg)
            st.rerun()
        else:
            st.error("Badge Number not found. Try again.")

# 3. EMPLOYEE ACTIVE: Data Display + Continuous Q&A
elif st.session_state.kiosk_state == "employee_active":
    emp = st.session_state.current_employee
    status_cls = "status-present" if "present" in emp["Status"].lower() else "status-leave"

    # Glass Card Display
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

    # Q&A Mic & Input
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
                start_prompt="🎙️ Ask",
                stop_prompt="⏹️",
                just_once=True,
                key="qa_mic_btn",
            )

    active_question = question_voice if question_voice else question_text
    if active_question:
        st.session_state.last_heard = active_question
        st.session_state.last_interaction = time.time()
        ans = answer_employee_question(emp, active_question)
        speak(ans)

    # Auto Reset Timer
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
