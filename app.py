"""
PXT HUB - Clean Cyber Kiosk with Real-Time Continuous Speech Recognition & Wake Word
"""

from __future__ import annotations

import os
import time
import json
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
            top: 8vh;
            left: 50%;
            transform: translateX(-50%);
            z-index: 30;
            text-align: center;
            pointer-events: none;
        }

        .hud-pxt-title {
            font-family: 'Inter', sans-serif;
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

        /* Top-Left HUD Indicator */
        .top-hud {
            position: fixed;
            top: 20px;
            left: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            z-index: 999999;
            background: rgba(10, 15, 30, 0.65);
            padding: 8px 16px;
            border-radius: 20px;
            border: 1px solid rgba(56, 189, 248, 0.3);
            backdrop-filter: blur(8px);
            font-family: 'Inter', sans-serif;
        }
        .dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #f59e0b;
            box-shadow: 0 0 8px #f59e0b, 0 0 16px rgba(245, 158, 11, 0.6);
            transition: background 0.3s ease, box-shadow 0.3s ease;
        }
        .dot.listening {
            background: #00e5ff !important;
            box-shadow: 0 0 12px #00e5ff, 0 0 24px #00e5ff !important;
            animation: dotPulse 1s infinite alternate;
        }
        @keyframes dotPulse {
            from { transform: scale(0.85); opacity: 0.8; }
            to   { transform: scale(1.35); opacity: 1; }
        }
        .status-txt {
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.08em;
            color: #fbbf24;
            text-transform: uppercase;
        }
        .status-txt.listening { color: #00e5ff !important; }

        /* Central Holographic Stage */
        .hologram-stage {
            position: fixed;
            top: 46%;
            left: 50%;
            transform: translate(-50%, -50%);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 48px;
            z-index: 5;
            pointer-events: none;
        }
        .wave-col {
            display: flex;
            align-items: center;
            gap: 6px;
            height: 130px;
        }
        .wave-col span {
            display: block;
            width: 5px;
            height: 18%;
            border-radius: 3px;
            background: linear-gradient(180deg, #7dd3fc, #0ea5e9);
            box-shadow: 0 0 8px rgba(56, 189, 248, 0.7);
            animation: waveBounce 1.6s ease-in-out infinite;
        }
        .wave-col span:nth-child(1) { animation-delay: 0.0s; }
        .wave-col span:nth-child(2) { animation-delay: 0.15s; }
        .wave-col span:nth-child(3) { animation-delay: 0.3s; }
        .wave-col span:nth-child(4) { animation-delay: 0.45s; }
        .wave-col span:nth-child(5) { animation-delay: 0.3s; }
        .wave-col span:nth-child(6) { animation-delay: 0.15s; }
        .wave-col span:nth-child(7) { animation-delay: 0.0s; }
        .wave-col span:nth-child(8) { animation-delay: 0.2s; }
        @keyframes waveBounce {
            0%, 100% { height: 12%; }
            50% { height: 90%; }
        }
        .hologram-stage.listening .wave-col span { animation-duration: 0.65s; }

        .ai-face {
            position: relative;
            width: 190px;
            height: 190px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .face-ring {
            position: absolute;
            border-radius: 50%;
            border: 1.5px solid rgba(56, 189, 248, 0.35);
            animation: ringSpin 7s linear infinite;
        }
        .ring-outer { width: 190px; height: 190px; border-color: rgba(56, 189, 248, 0.22); }
        .ring-mid   { width: 148px; height: 148px; border-color: rgba(56, 189, 248, 0.45); animation-direction: reverse; animation-duration: 4.5s; }
        @keyframes ringSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .hologram-stage.listening .ring-outer,
        .hologram-stage.listening .ring-mid { animation-duration: 1.6s; }

        .face-core {
            width: 112px;
            height: 112px;
            border-radius: 50%;
            background: radial-gradient(circle at 35% 30%, rgba(186, 230, 253, 0.95), rgba(14, 116, 144, 0.45) 55%, rgba(8, 20, 35, 0.92) 100%);
            box-shadow: 0 0 30px rgba(56, 189, 248, 0.55), 0 0 60px rgba(56, 189, 248, 0.3), inset 0 0 20px rgba(255, 255, 255, 0.15);
            display: flex;
            align-items: center;
            justify-content: center;
            animation: coreGlow 3s ease-in-out infinite;
        }
        @keyframes coreGlow {
            0%, 100% { box-shadow: 0 0 30px rgba(56, 189, 248, 0.5), 0 0 60px rgba(56, 189, 248, 0.25); }
            50%      { box-shadow: 0 0 46px rgba(56, 189, 248, 0.9), 0 0 92px rgba(56, 189, 248, 0.42); }
        }
        .hologram-stage.listening .face-core { animation-duration: 0.9s; }

        .face-core-inner {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: radial-gradient(circle at 40% 35%, rgba(255, 255, 255, 0.95), rgba(224, 247, 255, 0.15) 70%, transparent 100%);
            filter: drop-shadow(0 0 10px #7dd3fc);
        }

        /* Bottom Pill */
        .bottom-pill {
            position: fixed;
            bottom: 5vh;
            left: 50%;
            transform: translateX(-50%);
            z-index: 999999;
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(56, 189, 248, 0.45);
            border-radius: 30px;
            padding: 12px 26px;
            color: #38bdf8;
            font-family: 'Inter', sans-serif;
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.03em;
            max-width: 82%;
            text-align: center;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .bottom-pill.listening {
            color: #00e5ff;
            border-color: rgba(0, 229, 255, 0.6);
            box-shadow: 0 0 20px rgba(0, 229, 255, 0.35), 0 8px 24px rgba(0, 0, 0, 0.5);
        }

        /* Glass Deck */
        .kiosk-ui-container {
            position: fixed;
            bottom: 13vh;
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

        /* Hide the internal bridge input */
        .hidden-bridge-box {
            position: absolute !important;
            opacity: 0 !important;
            pointer-events: none !important;
            height: 0 !important;
            width: 0 !important;
        }

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

# Render Background & Static UI Elements
st.markdown(
    f"""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;700;800&display=swap" rel="stylesheet">

    <video id="kiosk-bg-video" autoplay loop muted playsinline>
        <source src="{active_video}" type="video/mp4">
    </video>

    <div class="hud-title-wrap">
        <div class="hud-pxt-title">{APP_TITLE}</div>
    </div>
    <a href="?switch_banner=true" target="_self" class="theme-dot-anchor" title="Switch Theme"></a>

    <div id="topHud" class="top-hud">
        <div id="micDot" class="dot"></div>
        <div id="statusLabel" class="status-txt">STANDBY</div>
    </div>

    <div id="hologramStage" class="hologram-stage">
        <div class="wave-col wave-left">
            <span></span><span></span><span></span><span></span>
            <span></span><span></span><span></span><span></span>
        </div>
        <div class="ai-face">
            <div class="face-ring ring-outer"></div>
            <div class="face-ring ring-mid"></div>
            <div class="face-core">
                <div class="face-core-inner"></div>
            </div>
        </div>
        <div class="wave-col wave-right">
            <span></span><span></span><span></span><span></span>
            <span></span><span></span><span></span><span></span>
        </div>
    </div>

    <div id="bottomPill" class="bottom-pill">🎙️ Say "Hi PXT" or Click here</div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# SPEECH SYNTHESIS & ROBUST MIC ENGINE (JS BRIDGE)
# ============================================================
current_state = st.session_state.get("kiosk_state", "idle")
current_emp = st.session_state.get("current_employee")

speak_text = ""
if current_state == "asked_badge" and not st.session_state.get("last_heard"):
    speak_text = "Please say or type your badge number."
elif current_state == "employee_active" and current_emp is not None and not st.session_state.get("last_heard"):
    speak_text = f"Welcome {current_emp['Name']}. What would you like to know?"

js_state_json = json.dumps(current_state)
js_speak_json = json.dumps(speak_text)

# Seamless event-driven JavaScript bridge
js_code = """
<script>
(function() {
    try {
        const pdoc = window.parent.document;
        const dot = pdoc.getElementById('micDot');
        const statusLabel = pdoc.getElementById('statusLabel');
        const bottomPill = pdoc.getElementById('bottomPill');
        const hologramStage = pdoc.getElementById('hologramStage');

        const currentKioskState = %CURRENT_STATE%;
        const textToSay = %SPEAK_TEXT%;

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {
            if (statusLabel) statusLabel.innerText = "CHROME NEEDED";
            if (bottomPill) bottomPill.innerText = "⚠️ Voice requires Google Chrome";
            return;
        }

        let recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        let isSpeaking = false;
        let isRecognizing = false;

        function updateUI(listening, customText) {
            if (!dot || !statusLabel || !bottomPill || !hologramStage) return;
            if (listening) {
                dot.className = 'dot listening';
                statusLabel.className = 'status-txt listening';
                statusLabel.innerText = 'LISTENING...';
                hologramStage.classList.add('listening');
                bottomPill.classList.add('listening');
                if (customText) bottomPill.innerText = customText;
            } else {
                dot.className = 'dot';
                statusLabel.className = 'status-txt';
                statusLabel.innerText = 'STANDBY';
                hologramStage.classList.remove('listening');
                bottomPill.classList.remove('listening');
                if (currentKioskState === 'idle') {
                    bottomPill.innerText = '🎙️ Say "Hi PXT" or Click here';
                } else if (currentKioskState === 'asked_badge') {
                    bottomPill.innerText = '🎙️ Speak Badge Number (e.g. EMP011)';
                } else {
                    bottomPill.innerText = '🎙️ Ask: "Leaves" or "Next off"';
                }
            }
        }

        // Send text to Streamlit without reloading the page
        function sendToStreamlit(val) {
            if (isSpeaking) return;
            const inputField = pdoc.querySelector('input[aria-label="hidden_voice_receiver"]');
            if (inputField) {
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                nativeInputValueSetter.call(inputField, val);
                inputField.dispatchEvent(new Event('input', { bubbles: true }));
                inputField.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: 'Enter', code: 'Enter', keyCode: 13 }));
            }
        }

        recognition.onstart = function() {
            isRecognizing = true;
            updateUI(true);
        };

        recognition.onresult = function(event) {
            if (isSpeaking) return;

            let liveText = '';
            let isFinal = false;

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                liveText += event.results[i][0].transcript;
                if (event.results[i].isFinal) isFinal = true;
            }

            liveText = liveText.trim();
            const lower = liveText.toLowerCase();

            if (liveText.length > 0) {
                updateUI(true, 'Heard: "' + liveText + '"');
            }

            if (currentKioskState === 'idle') {
                const normalized = lower.replace(/[^a-z0-9]/g, '');
                const isWakeTrigger = 
                    normalized.includes('pxt') || 
                    normalized.includes('pxd') || 
                    normalized.includes('txt') || 
                    normalized.includes('bxt') || 
                    normalized.includes('ext') || 
                    normalized.includes('hi') || 
                    normalized.includes('hello') || 
                    normalized.includes('hub');

                if (isWakeTrigger) {
                    sendToStreamlit('WAKE');
                }
            } else if (isFinal && liveText.length > 0) {
                sendToStreamlit(liveText);
            }
        };

        recognition.onerror = function(event) {
            if (event.error === 'not-allowed') {
                if (statusLabel) statusLabel.innerText = 'MIC BLOCKED';
                if (bottomPill) bottomPill.innerText = '🔒 Click to Allow Mic';
            }
        };

        recognition.onend = function() {
            isRecognizing = false;
            if (!isSpeaking) {
                setTimeout(safeStart, 100);
            }
        };

        function safeStart() {
            if (!isRecognizing && !isSpeaking) {
                try {
                    recognition.start();
                } catch(e) {}
            }
        }

        if (bottomPill) {
            bottomPill.onclick = function() {
                if (currentKioskState === 'idle') {
                    sendToStreamlit('WAKE');
                } else {
                    safeStart();
                }
            };
        }

        if (textToSay && 'speechSynthesis' in window) {
            isSpeaking = true;
            window.speechSynthesis.cancel();
            const ut = new SpeechSynthesisUtterance(textToSay);
            ut.rate = 0.95;
            ut.onend = function() {
                isSpeaking = false;
                safeStart();
            };
            ut.onerror = function() {
                isSpeaking = false;
                safeStart();
            };
            window.speechSynthesis.speak(ut);
        } else {
            safeStart();
        }

    } catch(err) {
        console.log('Bridge error:', err);
    }
})();
</script>
""".replace("%CURRENT_STATE%", js_state_json).replace("%SPEAK_TEXT%", js_speak_json)

components.html(js_code, height=0)

# Hidden Direct Bridge Receiver Input
st.markdown('<div class="hidden-bridge-box">', unsafe_allow_html=True)
bridge_val = st.text_input("hidden_voice_receiver", key="hidden_voice_receiver", label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

if bridge_val:
    val = bridge_val.strip()
    st.session_state["hidden_voice_receiver"] = ""
    st.session_state["last_interaction"] = time.time()
    
    if current_state == "idle" and ("WAKE" in val or "wake" in val.lower()):
        st.session_state["kiosk_state"] = "asked_badge"
        st.session_state["last_heard"] = ""
        st.rerun()
    elif current_state != "idle":
        st.session_state["last_heard"] = val
        st.rerun()

# ============================================================
# BOTTOM DECK (CARDS & INPUTS)
# ============================================================
st.markdown('<div class="kiosk-ui-container">', unsafe_allow_html=True)

# 1. State: Asked Badge
if current_state == "asked_badge":
    badge_in = st.text_input("badge_in", placeholder="Type Badge No (e.g. EMP011) or Speak", label_visibility="collapsed")
    active_input = st.session_state.get("last_heard") or badge_in

    if active_input and active_input != "WAKE":
        q = active_input.strip().lower().replace(" ", "").replace("-", "")
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

    q_box = st.text_input("ask_q", placeholder="Type: 'leaves left' or 'next off' or Speak", label_visibility="collapsed")
    active_q = st.session_state.get("last_heard") or q_box

    if active_q and active_q != "WAKE":
        st.session_state["last_interaction"] = time.time()
        ans = answer_employee_question(emp, active_q)
        st.session_state["last_heard"] = ""
        st.success(ans)

st.markdown('</div>', unsafe_allow_html=True)
