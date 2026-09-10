"""
PXT Hub - AI Voice Assistant
A full-screen, holographic kiosk-style workplace assistant: an animated AI
"orb" listens for voice or text, then surfaces staff attendance/leave info
on a floating glass card that auto-resets after a few seconds of idle time.
"""

from __future__ import annotations

import io
import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ---- Optional dependencies (handled gracefully if missing) ----
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
# CONFIG
# ============================================================
APP_TITLE = "PXT HUB"
DATA_FILE = "staff_data.csv"
ADMIN_PASSWORD = "pxt123"
REQUIRED_COLUMNS = ["EmployeeID", "Name", "Status", "RemainingLeaves", "NextOffDay", "Aliases"]
RESET_DELAY_SECONDS = 6
LANGUAGE_OPTIONS = {"English": "en", "Hindi": "hi-IN", "Urdu": "ur-PK"}

st.set_page_config(
    page_title=f"{APP_TITLE} - AI Voice Assistant",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# KIOSK FULL-SCREEN THEME (CSS INJECTION)
# ============================================================
def inject_kiosk_css() -> None:
    st.markdown(
        """
        <style>
            /* ---- Hide Streamlit chrome ---- */
            #MainMenu {visibility: hidden;}
            header[data-testid="stHeader"] {display: none;}
            footer {visibility: hidden;}
            div[data-testid="stToolbar"] {visibility: hidden; height: 0;}
            div[data-testid="stDecoration"] {display: none;}
            div[data-testid="stStatusWidget"] {visibility: hidden;}
            [data-testid="collapsedControl"] {opacity: 0.3; transition: opacity .2s ease;}
            [data-testid="collapsedControl"]:hover {opacity: 1;}

            /* ---- Full-screen dark stage ---- */
            html, body, [data-testid="stAppViewContainer"], .stApp {
                background: radial-gradient(circle at 50% 20%, #0d1220 0%, #05070c 55%, #020305 100%);
                color: #e9edf5;
                font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
            }
            [data-testid="stAppViewContainer"] > .main {
                padding-top: 0;
            }
            .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
                max-width: 760px;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }
            ::-webkit-scrollbar {width: 7px; height: 7px;}
            ::-webkit-scrollbar-thumb {background: rgba(126,224,255,0.25); border-radius: 10px;}
            ::-webkit-scrollbar-track {background: transparent;}

            /* ---- Sidebar (hidden admin) ---- */
            section[data-testid="stSidebar"] {
                background: #0a0d14;
                border-right: 1px solid rgba(255,255,255,0.06);
            }
            section[data-testid="stSidebar"] * {color: #e9edf5;}

            /* ---- Status pill (top) ---- */
            .kiosk-pill-row {text-align: center; margin-bottom: 0.6rem;}
            .kiosk-pill {
                display: inline-block;
                padding: 0.35rem 1.1rem;
                border-radius: 999px;
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.14);
                font-size: 0.8rem;
                font-weight: 600;
                letter-spacing: 0.03em;
                color: #cfe6ff;
                backdrop-filter: blur(6px);
            }

            /* ---- Orb stage ---- */
            .orb-stage {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.8rem;
                margin: 0.6rem 0 0 0;
            }
            .eq-row {
                display: flex;
                align-items: center;
                gap: 4px;
                height: 130px;
            }
            .eq-bar {
                width: 5px;
                border-radius: 4px;
                align-self: center;
                animation-name: eqPulse;
                animation-iteration-count: infinite;
                animation-timing-function: ease-in-out;
                transform-origin: center;
            }
            .eq-left .eq-bar {background: linear-gradient(180deg, #7ee0ff, #3b6cff);}
            .eq-right .eq-bar {background: linear-gradient(180deg, #ff9ed8, #b998ff);}
            @keyframes eqPulse {
                0%, 100% {transform: scaleY(0.25); opacity: 0.55;}
                50% {transform: scaleY(1); opacity: 1;}
            }

            .orb-wrapper {
                position: relative;
                width: 230px;
                height: 230px;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
            }
            .halo-ring {
                position: absolute;
                border-radius: 50%;
                border: 1.5px solid transparent;
            }
            .halo-ring.ring-1 {
                width: 230px; height: 230px;
                border-top-color: rgba(126,224,255,0.55);
                border-right-color: rgba(185,152,255,0.35);
                animation: rotateRing 9s linear infinite;
            }
            .halo-ring.ring-2 {
                width: 190px; height: 190px;
                border-bottom-color: rgba(255,158,216,0.45);
                border-left-color: rgba(126,224,255,0.3);
                animation: rotateRing 13s linear infinite reverse;
            }
            @keyframes rotateRing {from {transform: rotate(0deg);} to {transform: rotate(360deg);}}

            .orb-glow {
                position: absolute;
                width: 150px; height: 150px;
                border-radius: 50%;
                background: radial-gradient(circle, rgba(126,224,255,0.35) 0%, rgba(126,224,255,0) 70%);
                animation: pulseGlow 3s ease-in-out infinite;
            }
            @keyframes pulseGlow {
                0%, 100% {opacity: 0.55; transform: scale(1);}
                50% {opacity: 0.9; transform: scale(1.08);}
            }
            .orb-svg {
                position: relative;
                width: 150px;
                filter: drop-shadow(0 0 18px rgba(126,224,255,0.55));
                animation: pulseGlow 4s ease-in-out infinite;
            }
            .pxthub-label {
                position: absolute;
                bottom: 6px;
                left: 0; right: 0;
                text-align: center;
                font-size: 0.78rem;
                font-weight: 800;
                letter-spacing: 0.35em;
                color: #f2f4fa;
                text-shadow: 0 0 12px rgba(126,224,255,0.7);
            }

            /* ---- Kiosk glass card ---- */
            .kiosk-card {
                background: rgba(255,255,255,0.06);
                backdrop-filter: blur(18px);
                -webkit-backdrop-filter: blur(18px);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 24px;
                padding: 1.6rem 1.9rem;
                margin: -0.5rem auto 1rem auto;
                max-width: 460px;
                box-shadow: 0 18px 50px rgba(0,0,0,0.55);
                position: relative;
                z-index: 2;
                text-align: center;
            }
            .kiosk-card-name {font-size: 1.6rem; font-weight: 800; color: #fff; margin-bottom: 0.15rem;}
            .kiosk-card-id {color: #8a93ab; font-size: 0.85rem; margin-bottom: 1rem; letter-spacing: 0.04em;}
            .kiosk-grid {display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.7rem;}
            .kiosk-stat {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 14px;
                padding: 0.7rem 0.5rem;
            }
            .kiosk-stat-label {font-size: 0.66rem; letter-spacing: 0.07em; text-transform: uppercase; color: #7c8aa8; margin-bottom: 0.2rem;}
            .kiosk-stat-value {font-size: 1.05rem; font-weight: 700;}
            .status-present {color: #4ee6a4;}
            .status-leave {color: #ffb877;}
            .status-other {color: #7ee0ff;}

            /* ---- Bottom caption bar ---- */
            .kiosk-caption {text-align: center; margin: 0.2rem 0 1.4rem 0;}
            .kiosk-caption-main {font-size: 1.0rem; font-weight: 700; color: #f2f4fa;}
            .kiosk-caption-sub {font-size: 0.8rem; color: #6d7793; margin-top: 0.15rem;}

            /* ---- Search / mic controls ---- */
            div[data-testid="stTextInput"] input {
                background: rgba(255,255,255,0.06) !important;
                border: 1px solid rgba(255,255,255,0.14) !important;
                border-radius: 16px !important;
                color: #f2f4fa !important;
                padding: 0.8rem 1.05rem !important;
                font-size: 1.0rem !important;
                height: 3.1rem;
            }
            div[data-testid="stTextInput"] input:focus {
                border-color: #7ee0ff !important;
                box-shadow: 0 0 0 3px rgba(126,224,255,0.15) !important;
            }
            div[data-testid="stTextInput"] input::placeholder {color: #5f6a85 !important;}

            .stButton > button {
                background: linear-gradient(135deg, #2a3454 0%, #1a2036 100%);
                color: #f2f4fa;
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 16px;
                height: 3.1rem;
                font-weight: 600;
                width: 100%;
                transition: all 0.15s ease;
            }
            .stButton > button:hover {
                border-color: #7ee0ff;
                box-shadow: 0 0 0 3px rgba(126,224,255,0.15);
                color: #7ee0ff;
            }

            div[role="radiogroup"] {justify-content: center;}
            div[role="radiogroup"] label {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 999px;
                padding: 0.25rem 0.9rem !important;
                margin: 0 0.2rem !important;
            }

            div[data-testid="stAlert"] {
                background: rgba(255,255,255,0.05);
                border-radius: 16px;
                border: 1px solid rgba(255,255,255,0.10);
            }

            audio {width: 100%; margin-top: 0.8rem; border-radius: 12px;}

            .kiosk-footer {text-align: center; color: #4c5670; font-size: 0.74rem; margin-top: 1.6rem; letter-spacing: 0.03em;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_orb(count_per_side: int = 14) -> None:
    """Render the animated holographic head + left/right audio waveforms."""

    def eq_bars(side: str) -> str:
        bars = []
        for i in range(count_per_side):
            duration = 0.6 + (i % 5) * 0.15
            delay = (i % 7) * 0.08
            height = 30 + (i % 4) * 18
            bars.append(
                f'<span class="eq-bar" style="animation-duration:{duration}s;'
                f'animation-delay:{delay}s;height:{height}%;"></span>'
            )
        return f'<div class="eq-row eq-{side}">{"".join(bars)}</div>'

    head_svg = """
    <svg class="orb-svg" viewBox="0 0 300 340" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <pattern id="gridPattern" width="14" height="14" patternUnits="userSpaceOnUse">
                <path d="M14 0 L0 0 0 14" fill="none" stroke="rgba(126,224,255,0.4)" stroke-width="0.7"/>
            </pattern>
            <linearGradient id="strokeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#7ee0ff"/>
                <stop offset="100%" stop-color="#b998ff"/>
            </linearGradient>
        </defs>
        <path d="M150,18 C102,18 72,66 72,124 C72,156 84,178 100,194 L62,228
                 C50,250 44,282 44,322 L256,322 C256,282 250,250 238,228
                 L200,194 C216,178 228,156 228,124 C228,66 198,18 150,18 Z"
              fill="url(#gridPattern)" stroke="url(#strokeGrad)" stroke-width="1.6" opacity="0.95"/>
        <circle cx="150" cy="120" r="70" fill="none" stroke="rgba(126,224,255,0.25)" stroke-width="1"/>
    </svg>
    """

    st.markdown(
        f"""
        <div class="orb-stage">
            {eq_bars("left")}
            <div class="orb-wrapper">
                <div class="halo-ring ring-1"></div>
                <div class="halo-ring ring-2"></div>
                <div class="orb-glow"></div>
                {head_svg}
                <div class="pxthub-label">{APP_TITLE}</div>
            </div>
            {eq_bars("right")}
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_auto_reset(delay_seconds: float) -> None:
    """Force a full page reload after N seconds so the kiosk returns to idle."""
    components.html(
        f"""
        <script>
            setTimeout(function() {{
                try {{ window.parent.location.reload(); }} catch (e) {{}}
            }}, {int(delay_seconds * 1000)});
        </script>
        """,
        height=0,
    )


# ============================================================
# DATA HANDLING
# ============================================================
def _demo_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"EmployeeID": "EMP001", "Name": "Ayesha Khan", "Status": "Present",
             "RemainingLeaves": 12, "NextOffDay": "Saturday", "Aliases": "Ayesha|A. Khan|Ayesha K"},
            {"EmployeeID": "EMP002", "Name": "Bilal Ahmed", "Status": "On Leave",
             "RemainingLeaves": 5, "NextOffDay": "Sunday", "Aliases": "Bilal|B. Ahmed"},
            {"EmployeeID": "EMP011", "Name": "Usman", "Status": "Present",
             "RemainingLeaves": 20, "NextOffDay": "Friday", "Aliases": "Usman|EMP011"},
        ]
    )


@st.cache_data(show_spinner=False)
def load_staff_data(file_path: str, mtime: float | None) -> pd.DataFrame:
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path, dtype=str).fillna("")
            missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
            if missing:
                st.warning(f"'{file_path}' is missing required columns {missing}. Using demo data instead.")
                return _demo_data()
            return df[REQUIRED_COLUMNS].copy()
        except Exception as e:
            st.warning(f"Could not read '{file_path}' ({e}). Using demo data instead.")
            return _demo_data()
    return _demo_data()


def get_file_mtime(file_path: str):
    return os.path.getmtime(file_path) if os.path.exists(file_path) else None


def save_staff_data(uploaded_file) -> tuple[bool, str]:
    try:
        df = pd.read_csv(uploaded_file, dtype=str).fillna("")
    except Exception as e:
        return False, f"Could not parse CSV: {e}"

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return False, f"Uploaded CSV is missing required columns: {missing}"

    df[REQUIRED_COLUMNS].to_csv(DATA_FILE, index=False)
    return True, f"Staff data updated successfully ({len(df)} records)."


# ============================================================
# SEARCH
# ============================================================
def search_staff(df: pd.DataFrame, query: str) -> pd.DataFrame:
    if not query or not query.strip():
        return pd.DataFrame(columns=df.columns)

    q = query.strip().lower()

    def row_matches(row) -> bool:
        if q in str(row["EmployeeID"]).lower():
            return True
        if q in str(row["Name"]).lower():
            return True
        aliases = [a.strip().lower() for a in str(row["Aliases"]).split("|") if a.strip()]
        return any(q in alias for alias in aliases)

    return df[df.apply(row_matches, axis=1)]


# ============================================================
# TEXT-TO-SPEECH
# ============================================================
def generate_speech(text: str):
    if not TTS_AVAILABLE:
        return None
    try:
        buf = io.BytesIO()
        gTTS(text=text, lang="en").write_to_fp(buf)
        buf.seek(0)
        return buf
    except Exception:
        return None


def build_speech_text(row) -> str:
    return (
        f"{row['Name']}. Status: {row['Status']}. "
        f"Remaining leaves: {row['RemainingLeaves']}. "
        f"Next off day: {row['NextOffDay']}."
    )


def status_class(status: str) -> str:
    s = str(status).strip().lower()
    if "present" in s:
        return "status-present"
    if "leave" in s or "off" in s:
        return "status-leave"
    return "status-other"


# ============================================================
# SESSION STATE
# ============================================================
defaults = {
    "prefill_query": "",
    "reset_counter": 0,
    "input_source": None,
    "detected_language": "English",
    "result_shown_at": None,
    "last_shown_query": None,
    "admin_authenticated": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

inject_kiosk_css()

# Auto-clear the kiosk back to idle once the reset delay has elapsed
if st.session_state.result_shown_at and (time.time() - st.session_state.result_shown_at) > RESET_DELAY_SECONDS:
    st.session_state.prefill_query = ""
    st.session_state.reset_counter += 1
    st.session_state.result_shown_at = None
    st.session_state.last_shown_query = None
    st.session_state.input_source = None


# ============================================================
# SIDEBAR - HIDDEN ADMIN PANEL
# ============================================================
with st.sidebar:
    st.markdown("### 🔐 Admin Access")

    if not st.session_state.admin_authenticated:
        with st.expander("Staff data management", expanded=False):
            pwd = st.text_input("Admin password", type="password", key="admin_pwd")
            if st.button("Login", use_container_width=True):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
    else:
        st.success("Authenticated as admin.")
        if st.button("Log out", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.rerun()

        st.divider()
        st.markdown("**Upload updated staff CSV**")
        st.caption(f"Required columns: {', '.join(REQUIRED_COLUMNS)}")

        uploaded = st.file_uploader("Choose a CSV file", type=["csv"])
        if uploaded is not None and st.button("Save & overwrite staff_data.csv", use_container_width=True):
            ok, message = save_staff_data(uploaded)
            if ok:
                st.success(message)
                load_staff_data.clear()
                st.rerun()
            else:
                st.error(message)

        st.divider()
        st.markdown("**Current dataset preview**")
        current_df = load_staff_data(DATA_FILE, get_file_mtime(DATA_FILE))
        st.dataframe(current_df, use_container_width=True, hide_index=True)
        st.caption(f"{len(current_df)} record(s) loaded.")


# ============================================================
# MAIN - LOAD DATA
# ============================================================
staff_df = load_staff_data(DATA_FILE, get_file_mtime(DATA_FILE))


# ============================================================
# MAIN - STATUS PILL + ORB
# ============================================================
if st.session_state.input_source == "voice":
    pill_text = f"Heard: {st.session_state.detected_language}"
elif st.session_state.input_source == "text":
    pill_text = "Heard: Typed Input"
else:
    pill_text = "🎧 Awaiting your voice or text"

st.markdown(f'<div class="kiosk-pill-row"><span class="kiosk-pill">{pill_text}</span></div>', unsafe_allow_html=True)
render_orb()


# ============================================================
# MAIN - SEARCH CONTROLS
# ============================================================
reset_counter = st.session_state.reset_counter

lang_label = st.radio(
    "Recognition language",
    list(LANGUAGE_OPTIONS.keys()),
    horizontal=True,
    label_visibility="collapsed",
    key="lang_select",
)

col_text, col_mic = st.columns([4, 1])

with col_text:
    text_query = st.text_input(
        "Search",
        value=st.session_state.prefill_query,
        placeholder="Type a name, Employee ID, or alias…",
        label_visibility="collapsed",
        key=f"text_query_input_{reset_counter}",
    )

with col_mic:
    voice_text = None
    if MIC_AVAILABLE:
        voice_text = speech_to_text(
            language=LANGUAGE_OPTIONS[lang_label],
            start_prompt="🎤 Speak",
            stop_prompt="⏹️ Stop",
            just_once=True,
            use_container_width=True,
            key=f"mic_recorder_{reset_counter}",
        )
    else:
        st.button("🎤 Speak", disabled=True, use_container_width=True,
                   help="Install streamlit-mic-recorder to enable voice input")

if voice_text:
    st.session_state.prefill_query = voice_text
    st.session_state.input_source = "voice"
    st.session_state.detected_language = lang_label
    st.session_state.reset_counter += 1
    st.rerun()

active_query = text_query
if active_query and active_query != st.session_state.prefill_query:
    st.session_state.input_source = "text"
elif not active_query:
    st.session_state.input_source = None


# ============================================================
# MAIN - RESULT CARD + BOTTOM CAPTION
# ============================================================
if active_query and active_query.strip():
    results = search_staff(staff_df, active_query)

    if results.empty:
        st.session_state.result_shown_at = None
        st.session_state.last_shown_query = None
        st.markdown(
            '<div class="kiosk-caption">'
            '<div class="kiosk-caption-main">I couldn\'t find that record</div>'
            f'<div class="kiosk-caption-sub">No match for "{active_query}" — try another name, ID, or alias</div>'
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        if st.session_state.last_shown_query != active_query:
            st.session_state.result_shown_at = time.time()
            st.session_state.last_shown_query = active_query

        row = results.iloc[0]
        pill_class = status_class(row["Status"])
        st.markdown(
            f"""
            <div class="kiosk-card">
                <div class="kiosk-card-name">{row['Name']}</div>
                <div class="kiosk-card-id">{row['EmployeeID']}</div>
                <div class="kiosk-grid">
                    <div class="kiosk-stat">
                        <div class="kiosk-stat-label">Status</div>
                        <div class="kiosk-stat-value {pill_class}">{row['Status']}</div>
                    </div>
                    <div class="kiosk-stat">
                        <div class="kiosk-stat-label">Leaves Left</div>
                        <div class="kiosk-stat-value">{row['RemainingLeaves']}</div>
                    </div>
                    <div class="kiosk-stat">
                        <div class="kiosk-stat-label">Next Off Day</div>
                        <div class="kiosk-stat-value">{row['NextOffDay']}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="kiosk-caption">'
            f'<div class="kiosk-caption-main">Here is your update, {row["Name"]}</div>'
            '<div class="kiosk-caption-sub">Resetting shortly…</div>'
            "</div>",
            unsafe_allow_html=True,
        )

        if TTS_AVAILABLE:
            audio_buf = generate_speech(build_speech_text(row))
            if audio_buf is not None:
                st.audio(audio_buf, format="audio/mp3")

        if not st.session_state.admin_authenticated:
            inject_auto_reset(RESET_DELAY_SECONDS)
else:
    st.session_state.result_shown_at = None
    st.session_state.last_shown_query = None
    st.markdown(
        '<div class="kiosk-caption">'
        '<div class="kiosk-caption-main">Say a name or Employee ID to get started</div>'
        '<div class="kiosk-caption-sub">Tap the mic or type below</div>'
        "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# FOOTER
# ============================================================
st.markdown(
    f'<div class="kiosk-footer">PXT Hub · Kiosk session {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>',
    unsafe_allow_html=True,
)
