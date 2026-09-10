"""
PXT Hub - AI Voice Assistant
A dark-themed, kiosk-style workplace dashboard for staff attendance/leave
lookup via text or voice, with a hidden admin panel for CSV data management.
"""

from __future__ import annotations

import os
import io
from datetime import datetime

import pandas as pd
import streamlit as st

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
APP_TITLE = "PXT Hub"
APP_SUBTITLE = "AI Voice Assistant"
DATA_FILE = "staff_data.csv"
ADMIN_PASSWORD = "pxt123"
BANNER_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner.mp4"
REQUIRED_COLUMNS = ["EmployeeID", "Name", "Status", "RemainingLeaves", "NextOffDay", "Aliases"]

st.set_page_config(
    page_title=f"{APP_TITLE} - {APP_SUBTITLE}",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ============================================================
# KIOSK DARK THEME (CSS INJECTION)
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
            [data-testid="collapsedControl"] {
                opacity: 0.35;
                transition: opacity 0.2s ease;
            }
            [data-testid="collapsedControl"]:hover {opacity: 1;}

            /* ---- Global kiosk background ---- */
            html, body, [data-testid="stAppViewContainer"], .stApp {
                background: radial-gradient(circle at 50% 0%, #10141f 0%, #05070c 55%, #05070c 100%);
                color: #e9edf5;
                font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
            }
            [data-testid="stAppViewContainer"] > .main {
                padding-top: 1.2rem;
            }
            .block-container {
                padding-top: 1.5rem;
                padding-bottom: 3rem;
                max-width: 820px;
            }

            /* ---- Sidebar (admin) styling ---- */
            section[data-testid="stSidebar"] {
                background: #0a0d14;
                border-right: 1px solid rgba(255,255,255,0.06);
            }
            section[data-testid="stSidebar"] * {
                color: #e9edf5;
            }

            /* ---- Kiosk header ---- */
            .kiosk-eyebrow {
                text-align: center;
                letter-spacing: 0.35em;
                font-size: 0.72rem;
                font-weight: 600;
                color: #7c8aa8;
                text-transform: uppercase;
                margin-bottom: 0.2rem;
            }
            .kiosk-title {
                text-align: center;
                font-size: 2.4rem;
                font-weight: 800;
                margin: 0 0 0.3rem 0;
                background: linear-gradient(90deg, #7ee0ff 0%, #b998ff 55%, #ff9ed8 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .kiosk-subtitle {
                text-align: center;
                color: #8a93ab;
                font-size: 0.95rem;
                margin-bottom: 1.6rem;
            }

            /* ---- Video banner wrapper ---- */
            .kiosk-video-wrapper {
                position: relative;
                width: 100%;
                border-radius: 22px;
                overflow: hidden;
                box-shadow: 0 20px 60px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.05);
                margin-bottom: 1.8rem;
            }
            .kiosk-video-wrapper video {
                width: 100%;
                height: auto;
                max-height: 320px;
                object-fit: cover;
                display: block;
                pointer-events: none;
            }
            .kiosk-video-wrapper::after {
                content: "";
                position: absolute;
                inset: 0;
                background: linear-gradient(180deg, rgba(5,7,12,0) 55%, rgba(5,7,12,0.85) 100%);
            }

            /* ---- Section labels ---- */
            .kiosk-section-label {
                text-align: center;
                color: #7c8aa8;
                font-size: 0.8rem;
                font-weight: 600;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                margin: 0.4rem 0 0.8rem 0;
            }

            /* ---- Search input ---- */
            div[data-testid="stTextInput"] input {
                background: rgba(255,255,255,0.06) !important;
                border: 1px solid rgba(255,255,255,0.12) !important;
                border-radius: 16px !important;
                color: #f2f4fa !important;
                padding: 0.85rem 1.1rem !important;
                font-size: 1.05rem !important;
                height: 3.2rem;
            }
            div[data-testid="stTextInput"] input:focus {
                border-color: #7ee0ff !important;
                box-shadow: 0 0 0 3px rgba(126,224,255,0.15) !important;
            }
            div[data-testid="stTextInput"] input::placeholder {
                color: #5f6a85 !important;
            }

            /* ---- Buttons (mic + generic) ---- */
            .stButton > button, .stFormSubmitButton > button {
                background: linear-gradient(135deg, #2a3454 0%, #1a2036 100%);
                color: #f2f4fa;
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 16px;
                height: 3.2rem;
                font-weight: 600;
                font-size: 1.0rem;
                transition: all 0.15s ease;
            }
            .stButton > button:hover, .stFormSubmitButton > button:hover {
                border-color: #7ee0ff;
                box-shadow: 0 0 0 3px rgba(126,224,255,0.15);
                color: #7ee0ff;
            }

            /* mic_recorder widget buttons */
            div[data-testid="stHorizontalBlock"] button {
                border-radius: 16px !important;
            }

            /* ---- Result card (glassmorphism) ---- */
            .kiosk-card {
                background: rgba(255,255,255,0.05);
                backdrop-filter: blur(18px);
                -webkit-backdrop-filter: blur(18px);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 24px;
                padding: 1.8rem 2rem;
                margin-top: 1.4rem;
                box-shadow: 0 15px 45px rgba(0,0,0,0.45);
            }
            .kiosk-card-name {
                font-size: 1.7rem;
                font-weight: 800;
                color: #ffffff;
                margin-bottom: 0.15rem;
            }
            .kiosk-status-pill {
                display: inline-block;
                padding: 0.28rem 0.9rem;
                border-radius: 999px;
                font-size: 0.82rem;
                font-weight: 700;
                letter-spacing: 0.03em;
                margin-bottom: 1.2rem;
            }
            .status-present {
                background: rgba(56, 224, 148, 0.16);
                color: #4ee6a4;
                border: 1px solid rgba(78, 230, 164, 0.35);
            }
            .status-leave {
                background: rgba(255, 158, 91, 0.16);
                color: #ffb877;
                border: 1px solid rgba(255, 184, 119, 0.35);
            }
            .status-other {
                background: rgba(126, 224, 255, 0.14);
                color: #7ee0ff;
                border: 1px solid rgba(126, 224, 255, 0.35);
            }

            .kiosk-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 0.9rem;
                margin-top: 0.4rem;
            }
            .kiosk-stat {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 16px;
                padding: 0.85rem 1rem;
            }
            .kiosk-stat-label {
                font-size: 0.72rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: #7c8aa8;
                margin-bottom: 0.25rem;
            }
            .kiosk-stat-value {
                font-size: 1.15rem;
                font-weight: 700;
                color: #f2f4fa;
            }

            /* ---- Alerts restyled dark ---- */
            div[data-testid="stAlert"] {
                background: rgba(255,255,255,0.05);
                border-radius: 16px;
                border: 1px solid rgba(255,255,255,0.10);
            }

            /* ---- Footer ---- */
            .kiosk-footer {
                text-align: center;
                color: #4c5670;
                font-size: 0.78rem;
                margin-top: 2.5rem;
                letter-spacing: 0.04em;
            }

            audio {
                width: 100%;
                margin-top: 1rem;
                border-radius: 12px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# DATA HANDLING
# ============================================================
def _demo_data() -> pd.DataFrame:
    """Fallback demo records used when no CSV is present."""
    return pd.DataFrame(
        [
            {
                "EmployeeID": "EMP001",
                "Name": "Ayesha Khan",
                "Status": "Present",
                "RemainingLeaves": 12,
                "NextOffDay": "Saturday",
                "Aliases": "Ayesha|A. Khan|Ayesha K",
            },
            {
                "EmployeeID": "EMP002",
                "Name": "Bilal Ahmed",
                "Status": "On Leave",
                "RemainingLeaves": 5,
                "NextOffDay": "Sunday",
                "Aliases": "Bilal|B. Ahmed",
            },
            {
                "EmployeeID": "EMP003",
                "Name": "Sara Malik",
                "Status": "Present",
                "RemainingLeaves": 18,
                "NextOffDay": "Friday",
                "Aliases": "Sara|S. Malik|Sara M",
            },
        ]
    )


@st.cache_data(show_spinner=False)
def load_staff_data(file_path: str, mtime: float | None) -> pd.DataFrame:
    """
    Safely load staff data from CSV. Falls back to demo data if the file is
    missing, unreadable, or missing required columns.

    `mtime` is included purely to invalidate the cache when the underlying
    file changes (e.g. after an admin upload).
    """
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path, dtype=str).fillna("")
            missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
            if missing:
                st.warning(
                    f"'{file_path}' is missing required columns {missing}. "
                    "Using demo data instead."
                )
                return _demo_data()
            return df[REQUIRED_COLUMNS].copy()
        except Exception as e:
            st.warning(f"Could not read '{file_path}' ({e}). Using demo data instead.")
            return _demo_data()
    return _demo_data()


def get_file_mtime(file_path: str):
    return os.path.getmtime(file_path) if os.path.exists(file_path) else None


def save_staff_data(uploaded_file) -> tuple[bool, str]:
    """Validate and persist an uploaded CSV as the new staff_data.csv."""
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
    """Case-insensitive search across EmployeeID, Name, and pipe-separated Aliases."""
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

    mask = df.apply(row_matches, axis=1)
    return df[mask]


# ============================================================
# TEXT-TO-SPEECH
# ============================================================
def generate_speech(text: str):
    """Generate an in-memory MP3 for st.audio using gTTS. Returns None on failure."""
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


def status_pill_class(status: str) -> str:
    s = str(status).strip().lower()
    if "present" in s:
        return "status-present"
    if "leave" in s or "off" in s:
        return "status-leave"
    return "status-other"


# ============================================================
# SESSION STATE
# ============================================================
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False


# ============================================================
# APPLY THEME
# ============================================================
inject_kiosk_css()


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
        if uploaded is not None:
            if st.button("Save & overwrite staff_data.csv", use_container_width=True):
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
# MAIN PAGE - HEADER
# ============================================================
st.markdown('<div class="kiosk-eyebrow">Workplace Assistant</div>', unsafe_allow_html=True)
st.markdown(f'<div class="kiosk-title">{APP_TITLE} · {APP_SUBTITLE}</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="kiosk-subtitle">Ask about attendance, leave balances, and off days — by voice or text.</div>',
    unsafe_allow_html=True,
)


# ============================================================
# MAIN PAGE - SEAMLESS VIDEO BANNER (raw HTML5 <video>)
# ============================================================
st.markdown(
    f"""
    <div class="kiosk-video-wrapper">
        <video autoplay loop muted playsinline>
            <source src="{BANNER_URL}" type="video/mp4">
        </video>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# MAIN PAGE - SEARCH
# ============================================================
st.markdown('<div class="kiosk-section-label">🔍 Find a colleague</div>', unsafe_allow_html=True)

staff_df = load_staff_data(DATA_FILE, get_file_mtime(DATA_FILE))

col_text, col_mic = st.columns([4, 1])

with col_text:
    text_query = st.text_input(
        "Search",
        value=st.session_state.search_query,
        placeholder="Type a name, Employee ID, or alias…",
        label_visibility="collapsed",
        key="text_query_input",
    )

with col_mic:
    voice_text = None
    if MIC_AVAILABLE:
        voice_text = speech_to_text(
            language="en",
            start_prompt="🎤 Speak",
            stop_prompt="⏹️ Stop",
            just_once=True,
            use_container_width=True,
            key="mic_recorder",
        )
    else:
        st.button("🎤 Speak", disabled=True, use_container_width=True,
                   help="Install streamlit-mic-recorder to enable voice input")

# Voice input takes priority and auto-populates + triggers the search
active_query = text_query
if voice_text:
    active_query = voice_text
    st.session_state.search_query = voice_text
    st.rerun()


# ============================================================
# MAIN PAGE - RESULTS
# ============================================================
if active_query and active_query.strip():
    results = search_staff(staff_df, active_query)

    if results.empty:
        st.warning(f"No staff record found matching **'{active_query}'**.")
    else:
        for _, row in results.iterrows():
            pill_class = status_pill_class(row["Status"])
            st.markdown(
                f"""
                <div class="kiosk-card">
                    <div class="kiosk-card-name">{row['Name']}</div>
                    <span class="kiosk-status-pill {pill_class}">{row['Status']}</span>
                    <div class="kiosk-grid">
                        <div class="kiosk-stat">
                            <div class="kiosk-stat-label">Employee ID</div>
                            <div class="kiosk-stat-value">{row['EmployeeID']}</div>
                        </div>
                        <div class="kiosk-stat">
                            <div class="kiosk-stat-label">Remaining Leaves</div>
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

            if TTS_AVAILABLE:
                speech_text = build_speech_text(row)
                audio_buf = generate_speech(speech_text)
                if audio_buf is not None:
                    st.audio(audio_buf, format="audio/mp3")
else:
    st.info("Type a name/ID above or tap **Speak** to search for a colleague.")


# ============================================================
# FOOTER
# ============================================================
st.markdown(
    f'<div class="kiosk-footer">PXT Hub · Kiosk session started {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>',
    unsafe_allow_html=True,
)
