"""
PXT HUB - Clean Cyber Kiosk with Real-Time Continuous Speech Recognition & Wake Word
"""

from __future__ import annotations

import os
import time
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# CONFIGURATION
# ============================================================
APP_TITLE = "PXT HUB"
DATA_FILE = "staff_data.csv"
RESET_DELAY = 25

BANNER_1_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner.mp4"
BANNER_2_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner2.mp4"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Safe Session State
st.session_state.setdefault("active_banner", 1)
st.session_state.setdefault("kiosk_state", "idle")
st.session_state.setdefault("current_employee", None)
st.session_state.setdefault("last_heard", "")
st.session_state.setdefault("last_interaction", None)

# Switch banner check
if "switch_banner" in st.query_params:
    st.session_state.active_banner = 2 if st.session_state.active_banner == 1 else 1
    del st.query_params["switch_banner"]
    st.rerun()

# Receive voice input from JavaScript bridge
if "voice_payload" in st.query_params:
    spoken_val = st.query_params["voice_payload"].strip()
    del st.query_params["voice_payload"]
    st.session_state["last_heard"] = spoken_val
    st.session_state["last_interaction"] = time.time()
    
    current_state = st.session_state.get("kiosk_state", "idle")
    if current_state == "idle":
        st.session_state["kiosk_state"] = "asked_badge"
    st.rerun()

active_video = BANNER_1_URL if st.session_state.active_banner == 1 else BANNER_2_URL

# ============================================================
# DATA ENGINE
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

def answer_employee_question(emp, question: str) -> str:
    q = question.lower()
    name = emp['Name']
    if "leave" in q or "chutti" in q or "remaining" in q:
        return f"{name}, you have {emp['RemainingLeaves']} remaining leaves."
    elif "off" in q or "holiday" in q or "weekend" in q:
        return f"{name}, your next off day is on {emp['NextOffDay']}."
    elif "status" in q or "present" in q or "absent" in q:
        return f"{name}, your current status is {emp['Status']}."
    return f"{name}, status: {emp['Status']}, leaves: {emp['RemainingLeaves']}, next off: {emp['NextOffDay']}."

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
# CSS
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
            font-size: 1.6rem !important;
            font-weight: 800;
            letter-spacing: 0.25em;
            color: #ffffff;
            text-shadow: 0 0 16px rgba(56, 189, 248, 0.9), 0 0 30px rgba(56, 189, 248, 0.5);
            text-transform: uppercase;
        }

        .theme-dot-anchor {
            position: fixed;
            top: 20px;
            right: 25px;
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

        /* Glass Deck */
        .kiosk-ui-container {
            position: fixed;
            bottom: 4vh;
            left: 50%;
            transform: translateX(-50%);
            z-index: 200;
            width: 90%;
            max-width: 480px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }

        .employee-glass-card {
            background: rgba(11, 15, 25, 0.88);
            backdrop-filter: blur(25px);
            border: 1.5px solid rgba(56, 189, 248, 0.45);
            border-radius: 18px;
            padding: 1.1rem 1.4rem;
            width: 100%;
            text-align: center;
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.8);
        }

        .emp-name { font-size: 1.35rem; font-weight: 800; color: #ffffff; }
        .emp-badge { color: #38bdf8; font-size: 0.85rem; margin-bottom: 0.7rem; }
        .emp-stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
        .emp-stat-box { background: rgba(255, 255, 255, 0.05); border-radius: 10px; padding: 0.5rem 0.2rem; }
        .emp-stat-lbl { font-size: 0.62rem; color: #94a3b8; text-transform: uppercase; }
        .emp-stat-val { font-size: 1.05rem; font-weight: 700; margin-top: 2px; }
        .status-present { color: #34d399; }
        .status-leave { color: #fb923c; }

        div[data-testid="stTextInput"] input {
            background: rgba(15, 23, 42, 0.9) !important;
            border: 1.5px solid rgba(56, 189, 248, 0.45) !important;
            border-radius: 14px !important;
            color: #ffffff !important;
            height: 3rem;
            text-align: center;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Background Video & PXT Hub Title
st.markdown(
    f"""
    <video id="kiosk-bg-video" autoplay loop muted playsinline>
        <source src="{active_video}" type="video/mp4">
    </video>
    <div class="hud-title-wrap">
        <div class="hud-pxt-title">{APP_TITLE}</div>
    </div>
    <a href="?switch_banner=true" target="_self" class="theme-dot-anchor" title="Switch Theme"></a>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# LIVE VOICE RECOGNITION & HUD COMPONENT (JS BRIDGE)
# ============================================================
current_state = st.session_state.get("kiosk_state", "idle")
current_emp = st.session_state.get("current_employee")

speak_text = ""
if current_state == "asked_badge" and not st.session_state.get("last_interaction"):
    speak_text = "Hello! Please tell me your Badge Number."
elif current_state == "employee_active" and current_emp is not None and not st.session_state.get("last_heard"):
    speak_text = f"Welcome {current_emp['Name']}. How can I assist you today?"

components.html(
    f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;700;800&display=swap');
        * {{ font-family: 'Inter', sans-serif; box-sizing: border-box; }}
        
        .top-hud {{
            position: fixed;
            top: 15px;
            left: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            z-index: 999999;
            background: rgba(10, 15, 30, 0.65);
            padding: 6px 14px;
            border-radius: 20px;
            border: 1px solid rgba(56, 189, 248, 0.3);
            backdrop-filter: blur(8px);
        }}
        .dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #f59e0b;
            box-shadow: 0 0 8px #f59e0b;
            transition: all 0.3s ease;
        }}
        .dot.listening {{
            background: #00e5ff !important;
            box-shadow: 0 0 12px #00e5ff, 0 0 20px #00e5ff !important;
            animation: pulse 1s infinite alternate;
        }}
        @keyframes pulse {{
            from {{ transform: scale(0.9); opacity: 0.8; }}
            to {{ transform: scale(1.3); opacity: 1; }}
        }}
        .status-txt {{
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.08em;
            color: #94a3b8;
            text-transform: uppercase;
        }}
        .status-txt.listening {{
            color: #00e5ff !important;
        }}
        .live-capsule {{
            position: fixed;
            top: 15px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(56, 189, 248, 0.4);
            border-radius: 30px;
            padding: 5px 16px;
            color: #38bdf8;
            font-size: 13px;
            font-weight: 600;
            max-width: 65%;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            backdrop-filter: blur(10px);
            display: none;
            z-index: 999999;
        }}
        .mic-instruction {{
            position: fixed;
            top: 32vh;
            left: 50%;
            transform: translateX(-50%);
            text-align: center;
            z-index: 9999;
            color: rgba(255, 255, 255, 0.7);
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.05em;
            background: rgba(15, 23, 42, 0.6);
            padding: 8px 18px;
            border-radius: 20px;
            border: 1px solid rgba(56, 189, 248, 0.3);
            backdrop-filter: blur(6px);
            cursor: pointer;
        }}
    </style>

    <div class="top-hud">
        <div id="micDot" class="dot"></div>
        <div id="statusLabel" class="status-txt">STANDBY (SAY "HI PXT")</div>
    </div>

    <div id="liveHeard" class="live-capsule"></div>
    <div id="micPrompt" class="mic-instruction" onclick="activateMicDirectly()">🎙️ TAP OR SAY "HI PXT" TO WAKE</div>

    <script>
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        let recognition = null;
        let isSpeakingOrProcessing = false;
        const currentKioskState = "{current_state}";

        const dot = document.getElementById('micDot');
        const statusLabel = document.getElementById('statusLabel');
        const liveCapsule = document.getElementById('liveHeard');
        const promptBtn = document.getElementById('micPrompt');

        // Dynamic status display based on kiosk state
        if (currentKioskState !== "idle") {{
            dot.className = "dot listening";
            statusLabel.className = "status-txt listening";
            statusLabel.innerText = "LISTENING...";
            promptBtn.innerText = currentKioskState === "asked_badge" 
                ? "🎙️ SPEAK YOUR BADGE NUMBER (e.g. EMP011)" 
                : "🎙️ ASK: 'LEAVES LEFT' OR 'NEXT OFF'";
        }}

        // Text-To-Speech if message available
        const textToSay = "{speak_text}";
        if (textToSay && 'speechSynthesis' in window) {{
            isSpeakingOrProcessing = true;
            const utterance = new SpeechSynthesisUtterance(textToSay);
            utterance.rate = 0.95;
            utterance.onend = () => {{
                isSpeakingOrProcessing = false;
                startRecognitionEngine();
            }};
            window.speechSynthesis.speak(utterance);
        }}

        function setListeningVisuals(listening) {{
            if (listening) {{
                dot.className = 'dot listening';
                statusLabel.className = 'status-txt listening';
                statusLabel.innerText = 'LISTENING...';
            }} else {{
                if (currentKioskState === "idle") {{
                    dot.className = 'dot';
                    statusLabel.className = 'status-txt';
                    statusLabel.innerText = 'STANDBY (SAY "HI PXT")';
                }}
            }}
        }}

        function startRecognitionEngine() {{
            if (!SpeechRecognition) {{
                statusLabel.innerText = 'MIC NOT SUPPORTED';
                return;
            }}
            if (recognition) return;

            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            recognition.onstart = function() {{
                if (currentKioskState !== "idle") {{
                    setListeningVisuals(true);
                }}
            }};

            recognition.onresult = function(event) {{
                if (isSpeakingOrProcessing) return;

                let interim = '';
                let finalPhrase = '';

                for (let i = event.resultIndex; i < event.results.length; ++i) {{
                    const text = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {{
                        finalPhrase += text;
                    }} else {{
                        interim += text;
                    }}
                }}

                const heardText = (finalPhrase || interim).trim();
                const lowerText = heardText.toLowerCase();

                if (heardText.length > 0) {{
                    setListeningVisuals(true);
                    liveCapsule.style.display = 'block';
                    liveCapsule.innerText = 'Heard: ' + heardText;
                }}

                // Idle wake-word detection
                if (currentKioskState === "idle") {{
                    if (lowerText.includes("pxt") || lowerText.includes("hi pxt") || lowerText.includes("hey") || lowerText.includes("hello")) {{
                        isSpeakingOrProcessing = true;
                        window.parent.location.search = '?voice_payload=' + encodeURIComponent('WAKE');
                    }}
                }} else if (finalPhrase.trim().length > 0) {{
                    isSpeakingOrProcessing = true;
                    window.parent.location.search = '?voice_payload=' + encodeURIComponent(finalPhrase.trim());
                }}
            }};

            recognition.onerror = function(e) {{
                console.log("Mic error / pause: ", e.error);
            }};

            recognition.onend = function() {{
                // Auto-restart to maintain continuous listening
                recognition = null;
                if (!isSpeakingOrProcessing) {{
                    setTimeout(startRecognitionEngine, 250);
                }}
            }};

            try {{
                recognition.start();
            }} catch(e) {{}}
        }}

        function activateMicDirectly() {{
            if (currentKioskState === "idle") {{
                window.parent.location.search = '?voice_payload=' + encodeURIComponent('WAKE');
            }} else {{
                startRecognitionEngine();
            }}
        }}

        // Initialize listener
        startRecognitionEngine();
    </script>
    """,
    height=80,
)

# ============================================================
# BOTTOM DECK (CARDS & INPUTS)
# ============================================================
st.markdown('<div class="kiosk-ui-container">', unsafe_allow_html=True)

# 1. State: Asked Badge
if current_state == "asked_badge":
    badge_in = st.text_input("badge_in", placeholder="Type Badge No (e.g. EMP011) or Speak above", label_visibility="collapsed")
    active_input = st.session_state.get("last_heard") or badge_in

    if active_input and active_input != "WAKE":
        q = active_input.strip().lower().replace(" ", "")
        match = staff_df[staff_df["EmployeeID"].str.lower().str.replace(" ", "") == q]
        if match.empty:
            match = staff_df[staff_df["Name"].str.lower().str.contains(active_input.strip().lower())]

        if not match.empty:
            st.session_state["current_employee"] = match.iloc[0]
            st.session_state["kiosk_state"] = "employee_active"
            st.session_state["last_heard"] = ""
            st.session_state["last_interaction"] = time.time()
            st.rerun()
        elif badge_in:
            st.error("Badge Number not found. Please try again.")

# 2. State: Employee Active
elif current_state == "employee_active":
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

    q_box = st.text_input("ask_q", placeholder="Type: 'leaves left' or 'next off' or Speak above", label_visibility="collapsed")
    active_q = st.session_state.get("last_heard") or q_box

    if active_q and active_q != "WAKE":
        st.session_state["last_interaction"] = time.time()
        ans = answer_employee_question(emp, active_q)
        st.session_state["last_heard"] = ""
        st.success(ans)
        
        # Voice speak answer
        components.html(
            f"""
            <script>
                if ('speechSynthesis' in window) {{
                    const u = new SpeechSynthesisUtterance("{ans}");
                    u.rate = 0.95;
                    window.speechSynthesis.speak(u);
                }}
            </script>
            """,
            height=0,
        )

st.markdown('</div>', unsafe_allow_html=True)
