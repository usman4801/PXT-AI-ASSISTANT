"""
PXT HUB - Clean Full Screen Video Kiosk
Flow: Full screen video -> Say "Hi PXT" -> Ask Badge No -> Show Status -> Auto Reset
"""

from __future__ import annotations

import io
import os
import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ---- Audio / Voice Dependencies ----
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
RESET_DELAY = 8  # 8 seconds baad auto-reset
VIDEO_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner.mp4"

st.set_page_config(
    page_title="PXT HUB",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# 100% TRUE FULLSCREEN CSS (ZERO BORDERS / NO EXTRA TEXT)
# ============================================================
st.markdown(
    f"""
    <style>
        /* Streamlit UI elements hide */
        #MainMenu, header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="collapsedControl"] {{
            display: none !important;
            visibility: hidden !important;
        }}

        /* Full black viewport without scroll */
        html, body, [data-testid="stAppViewContainer"], .stApp {{
            background: #000000 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            height: 100vh !important;
            width: 100vw !important;
        }}

        .main, .main .block-container {{
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100vw !important;
            width: 100vw !important;
            height: 100vh !important;
        }}

        /* TRUE EDGE-TO-EDGE BACKGROUND VIDEO */
        #bg-video {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            object-fit: cover;
            z-index: 1;
        }}

        /* FLOATING INTERACTIVE OVERLAY */
        .kiosk-overlay {{
            position: fixed;
            bottom: 4vh;
            left: 50%;
            transform: translateX(-50%);
            z-index: 999;
            width: 90%;
            max-width: 520px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }}

        /* FLOATING GLASS RESULT CARD */
        .glass-card {{
            background: rgba(10, 15, 29, 0.85);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1.5px solid rgba(56, 189, 248, 0.4);
            border-radius: 20px;
            padding: 1.5rem;
            width: 100%;
            text-align: center;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8), 0 0 25px rgba(56, 189, 248, 0.3);
            animation: fadeIn 0.3s ease-out;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(15px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .card-name {{
            font-size: 1.6rem;
            font-weight: 800;
            color: #ffffff;
        }}
        .card-badge {{
            color: #38bdf8;
            font-size: 0.95rem;
            margin-bottom: 1rem;
            letter-spacing: 0.05em;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }}
        .stat-cell {{
            background: rgba(255, 255, 255, 0.06);
            border-radius: 12px;
            padding: 0.7rem 0.3rem;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .stat-lbl {{
            font-size: 0.68rem;
            color: #94a3b8;
            text-transform: uppercase;
        }}
        .stat-val {{
            font-size: 1.15rem;
            font-weight: 700;
            margin-top: 4px;
        }}
        .status-present {{ color: #34d399; }}
        .status-leave {{ color: #fb923c; }}

        /* INPUT CONTROLS */
        div[data-testid="stTextInput"] {{
            width: 100% !important;
        }}
        div[data-testid="stTextInput"] input {{
            background: rgba(15, 23, 42, 0.9) !important;
            border: 1.5px solid rgba(56, 189, 248, 0.5) !important;
            border-radius: 14px !important;
            color: #ffffff !important;
            height: 3.2rem;
            font-size: 1.1rem !important;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.6);
        }}
        div[data-testid="stTextInput"] input:focus {{
            border-color: #38bdf8 !important;
            box-shadow: 0 0 20px rgba(56, 189, 248, 0.5) !important;
        }}

        /* MIC BUTTON */
        .stButton > button {{
            background: rgba(15, 23, 42, 0.9) !important;
            border: 1.5px solid rgba(56, 189, 248, 0.5) !important;
            border-radius: 999px !important;
            color: #ffffff !important;
            height: 3rem !important;
            padding: 0 1.8rem !important;
            font-weight: 700;
            box-shadow: 0 4px 20px rgba(0,0,0,0.6);
        }}
        .stButton > button:hover {{
            border-color: #38bdf8 !important;
            color: #38bdf8 !important;
        }}
    </style>

    <video id="bg-video" autoplay loop muted playsinline>
        <source src="{VIDEO_URL}" type="video/mp4">
    </video>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA & SPEECH LOGIC
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

def speak(text):
    if not TTS_AVAILABLE:
        return
    try:
        buf = io.BytesIO()
        gTTS(text=text, lang="en").write_to_fp(buf)
        buf.seek(0)
        st.audio(buf, format="audio/mp3", autoplay=True)
    except Exception:
        pass

# States
if "state" not in st.session_state:
    st.session_state.state = "idle"  # idle -> asked_badge -> showing_result
if "matched_employee" not in st.session_state:
    st.session_state.matched_employee = None
if "result_time" not in st.session_state:
    st.session_state.result_time = None

# Auto Reset check
if st.session_state.result_time and (time.time() - st.session_state.result_time > RESET_DELAY):
    st.session_state.state = "idle"
    st.session_state.matched_employee = None
    st.session_state.result_time = None
    st.rerun()

staff_df = load_data()


# ============================================================
# INTERFACE LOGIC
# ============================================================
st.markdown('<div class="kiosk-overlay">', unsafe_allow_html=True)

# 1. IDLE STATE: Only Full Screen Video + Mic trigger
if st.session_state.state == "idle":
    if MIC_AVAILABLE:
        spoken = speech_to_text(
            language="en-US",
            start_prompt="🎙️ Say 'Hi PXT'",
            stop_prompt="⏹️ Listening...",
            just_once=True,
            key="idle_mic",
        )
        if spoken:
            if "pxt" in spoken.lower() or "hi" in spoken.lower():
                st.session_state.state = "asked_badge"
                speak("Hello! Please enter or say your Badge Number.")
                st.rerun()
    else:
        # Fallback button agar mic library na ho
        if st.button("🎙️ Tap to Start"):
            st.session_state.state = "asked_badge"
            speak("Hello! Please enter your Badge Number.")
            st.rerun()

# 2. ASKED BADGE STATE: Input box opens for Badge No
elif st.session_state.state == "asked_badge":
    badge_input = st.text_input(
        "badge_input",
        placeholder="Enter Badge No / Employee ID (e.g. EMP011)",
        label_visibility="collapsed",
        key="badge_box",
    )

    if MIC_AVAILABLE:
        badge_voice = speech_to_text(
            language="en-US",
            start_prompt="🎙️ Or Speak Badge No",
            stop_prompt="⏹️ Done",
            just_once=True,
            key="badge_mic",
        )
        if badge_voice:
            badge_input = badge_voice

    if badge_input:
        q = badge_input.strip().lower()
        match = staff_df[staff_df["EmployeeID"].str.lower() == q]
        if match.empty:
            match = staff_df[staff_df["Name"].str.lower().str.contains(q)]

        if not match.empty:
            st.session_state.matched_employee = match.iloc[0]
            st.session_state.state = "showing_result"
            st.session_state.result_time = time.time()
            st.rerun()
        else:
            st.error("Badge Number not found. Try again.")

# 3. SHOWING RESULT STATE: Clean Glass Card + Voice Answer
elif st.session_state.state == "showing_result":
    emp = st.session_state.matched_employee
    status_cls = "status-present" if "present" in emp["Status"].lower() else "status-leave"

    st.markdown(
        f"""
        <div class="glass-card">
            <div class="card-name">{emp['Name']}</div>
            <div class="card-badge">Badge No: {emp['EmployeeID']}</div>
            <div class="stats-grid">
                <div class="stat-cell">
                    <div class="stat-lbl">STATUS</div>
                    <div class="stat-val {status_cls}">{emp['Status']}</div>
                </div>
                <div class="stat-cell">
                    <div class="stat-lbl">LEAVES LEFT</div>
                    <div class="stat-val">{emp['RemainingLeaves']}</div>
                </div>
                <div class="stat-cell">
                    <div class="stat-lbl">NEXT OFF</div>
                    <div class="stat-val">{emp['NextOffDay']}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Voice Output in English
    response_msg = f"Welcome {emp['Name']}. Your status is {emp['Status']}. You have {emp['RemainingLeaves']} leaves remaining."
    speak(response_msg)

    # Auto reset timer trigger
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
