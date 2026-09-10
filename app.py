"""
PXT HUB - Clean Cyber Kiosk with Real-time Web Voice Recognition & Banner Switcher
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
# SESSION STATES
# ============================================================
if "active_banner" not in st.session_state:
    st.session_state.active_banner = 1
if "kiosk_state" not in st.session_state:
    st.session_state.kiosk_state = "idle"  # idle -> asked_badge -> employee_active
if "current_employee" not in st.session_state:
    st.session_state.current_employee = None
if "last_heard" not in st.session_state:
    st.session_state.last_heard = ""
if "last_interaction" not in st.session_state:
    st.session_state.last_interaction = None

# Query param checks (Browser voice direct update handle karta hai)
params = st.query_params
if "voice_input" in params and params["voice_input"]:
    heard_val = params["voice_input"].strip()
    st.session_state.last_heard = heard_val
    st.query_params.clear()

    if st.session_state.kiosk_state == "idle":
        if "pxt" in heard_val.lower() or "hi" in heard_val.lower():
            st.session_state.kiosk_state = "asked_badge"
            st.session_state.last_interaction = time.time()
            st.rerun()

    elif st.session_state.kiosk_state == "asked_badge":
        clean_id = heard_val.lower().replace(" ", "")
        st.session_state.temp_badge_search = clean_id
        st.rerun()


# ============================================================
# CLEAN & RESIZED HUD STYLING
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

        /* 100% Edge-to-Edge Fullscreen Video */
        #kiosk-bg-video {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            object-fit: cover;
            z-index: 1;
        }

        /* Compact & Elegant PXT HUB Title */
        .hud-title-wrap {
            position: fixed;
            top: 15vh;
            left: 50%;
            transform: translateX(-50%);
            z-index: 20;
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

        /* Top HUD Bar */
        .top-hud-bar {
            position: fixed;
            top: 15px;
            left: 0;
            width: 100vw;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 20px;
            z-index: 50;
            box-sizing: border-box;
            pointer-events: none;
        }

        /* Small Sleek Green Mic Dot */
        .mic-dot-container {
            display: flex;
            align-items: center;
            gap: 7px;
        }

        .green-mic-dot {
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            box-shadow: 0 0 10px #22c55e, 0 0 18px #22c55e;
            animation: pulseGreen 1.4s infinite ease-in-out;
        }

        @keyframes pulseGreen {
            0%, 100% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.3); opacity: 1; }
        }

        .mic-label {
            color: #4ade80;
            font-weight: 600;
            font-size: 0.65rem !important;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            opacity: 0.9;
        }

        /* Heard Capsule: Only visible when text exists */
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

        /* Top Right Theme Dot Button */
        .theme-dot-btn {
            position: fixed;
            top: 15px;
            right: 20px;
            z-index: 9999;
        }

        .theme-dot-btn button {
            width: 14px !important;
            height: 14px !important;
            min-height: 14px !important;
            border-radius: 50% !important;
            background: #38bdf8 !important;
            border: 1.5px solid #ffffff !important;
            box-shadow: 0 0 12px #38bdf8
