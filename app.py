"""
PXT HUB - AI Voice Assistant
Original Banner Layout with Glowing Video Frame, Mic & Floating Data Card
"""

from __future__ import annotations

import io
import os
import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ---- Optional dependencies ----
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
APP_TITLE = "PXT HUB"
DATA_FILE = "staff_data.csv"
ADMIN_PASSWORD = "pxt123"
REQUIRED_COLUMNS = ["EmployeeID", "Name", "Status", "RemainingLeaves", "NextOffDay", "Aliases"]
RESET_DELAY_SECONDS = 7
VIDEO_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner.mp4"

LANGUAGE_OPTIONS = {
    "Hindi / Urdu": "hi-IN",
    "English": "en"
}

st.set_page_config(
    page_title=f"{APP_TITLE} - AI Assistant",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CSS STYLING (MATCHING EXACT ORIGINAL UI)
# ============================================================
def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
            /* 1. Header / Streamlit UI hide */
            #MainMenu, header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {
                display: none !important;
                visibility: hidden !important;
            }
            [data-testid="collapsedControl"] {
                opacity: 0.2;
                transition: opacity 0.3s ease;
            }
            [data-testid="collapsedControl"]:hover {
                opacity: 1;
            }

            /* 2. Global Dark Theme */
            html, body, [data-testid="stAppViewContainer"], .stApp {
                background: #060913 !important;
                color: #ffffff !important;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            }

            .main .block-container {
                max-width: 680px !important;
                padding-top: 1.8rem !important;
                padding-bottom: 2rem !important;
                margin: 0 auto !important;
            }

            /* 3. Title */
            .pxt-title {
                text-align: center;
                font-size: 2.2rem;
                font-weight: 900;
                letter-spacing: 0.18em;
                color: #ffffff;
                text-transform: uppercase;
                margin-bottom: 1.2rem;
                text-shadow: 0 0 15px rgba(56, 189, 248, 0.75), 0 0 30px rgba(56, 189, 248, 0.3);
            }

            /* 4. Center Video Banner Frame */
            .video-frame-wrap {
                width: 100%;
                max-width: 650px;
                margin: 0 auto 1.4rem auto;
                border-radius: 22px;
                overflow: hidden;
                border: 1.5px solid rgba(56, 189, 248, 0.45);
                box-shadow: 0 0 35px rgba(56, 189, 248, 0.28), 0 10px 30px rgba(0, 0, 0, 0.7);
                background: #000000;
            }

            .video-frame-wrap video {
                width: 100%;
                height: auto;
                display: block;
                object-fit: cover;
                max-height: 340px;
            }

            /* 5. Status Pill */
            .pill-wrapper {
                text-align: center;
                margin-bottom: 1.2rem;
            }

            .status-pill {
                display: inline-flex;
                align-items: center;
                gap: 9px;
                padding: 0.45rem 1.4rem;
                border-radius: 999px;
                background: rgba(15, 23, 42, 0.8);
                border: 1px solid rgba(56, 189, 248, 0.35);
                box-shadow: 0 0 18px rgba(56, 189, 248, 0.2);
                font-size: 0.88rem;
                font-weight: 500;
                color: #cbebff;
            }

            .status-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #38bdf8;
                box-shadow: 0 0 10px #38bdf8;
                animation: pulseGlow 1.5s infinite ease-in-out;
            }

            @keyframes pulseGlow {
                0%, 100% { transform: scale(1); opacity: 0.7; }
                50% { transform: scale(1.4); opacity: 1; }
            }

            /* 6. Language Radio alignment */
            div[role="radiogroup"] {
                justify-content: center !important;
                margin-bottom: 1rem !important;
                gap: 1.5rem !important;
            }

            div[role="radiogroup"] label {
                color: #cbd5e1 !important;
                font-size: 0.95rem !important;
            }

            /* 7. Search Input & Button */
            div[data-testid="stTextInput"] input {
                background: rgba(15, 23, 42, 0.85) !important;
                border: 1px solid rgba(56, 189, 248, 0.35) !important;
                border-radius: 14px !important;
                color: #ffffff !important;
                height: 3.1rem;
                font-size: 0.98rem !important;
                padding-left: 1rem !important;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
            }

            div[data-testid="stTextInput"] input:focus {
                border-color: #38bdf8 !important;
                box-shadow: 0 0 15px rgba(56, 189, 248, 0.4) !important;
            }

            .stButton > button {
                background: #1e293b !important;
                border: 1px solid rgba(56, 189, 248, 0.4) !important;
                border-radius: 14px !important;
                color: #ffffff !important;
                height: 3.1rem !important;
                font-weight: 600;
                font-size: 0.95rem;
                transition: all 0.2s ease;
            }

            .stButton > button:hover {
                border-color: #38bdf8 !important;
                box-shadow: 0 0 15px rgba(56, 189, 248, 0.4) !important;
                color: #38bdf8 !important;
            }

            /* 8. Bottom Helper Text */
            .guide-wrap {
                text-align: center;
                margin-top: 1.4rem;
                margin-bottom: 1rem;
            }

            .guide-main {
                font-size: 1.25rem;
                font-weight: 700;
                color: #f8fafc;
                margin-bottom: 0.3rem;
            }

            .guide-sub {
                font-size: 0.88rem;
                color: #94a3b8;
            }

            /* 9. Employee Result Card */
            .result-card {
                background: rgba(15, 23, 42, 0.85);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 20px;
                padding: 1.4rem 1.8rem;
                margin: 1.2rem auto;
                max-width: 580px;
                text-align: center;
                box-shadow: 0 15px 35px rgba(0, 0, 0, 0.6), 0 0 25px rgba(56, 189, 248, 0.2);
            }

            .card-name {
                font-size: 1.6rem;
                font-weight: 800;
                color: #ffffff;
            }

            .card-id {
                color: #94a3b8;
                font-size: 0.85rem;
                letter-spacing: 0.08em;
                margin-bottom: 1rem;
            }

            .stats-row {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 0.8rem;
                margin-top: 0.8rem;
            }

            .stat-box {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 0.7rem 0.4rem;
            }

            .stat-lbl {
                font-size: 0.68rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: #94a3b8;
                margin-bottom: 0.25rem;
            }

            .stat-val {
                font-size: 1.15rem;
                font-weight: 700;
            }

            .status-present { color: #34d399; }
            .status-leave { color: #fb923c; }
            .status-other { color: #38bdf8; }

            audio {
                width: 100%;
                margin-top: 0.8rem;
                border-radius: 10px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_auto_reset(delay_seconds: float) -> None:
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
# DATA FUNCTIONS
# ============================================================
def _demo_data() -> pd.DataFrame:
    return pd.DataFrame([
        {"EmployeeID": "EMP001", "Name": "Ayesha Khan", "Status": "Present", "RemainingLeaves": "12", "NextOffDay": "Saturday", "Aliases": "Ayesha|Khan"},
        {"EmployeeID": "EMP002", "Name": "Bilal Ahmed", "Status": "On Leave", "RemainingLeaves": "5", "NextOffDay": "Sunday", "Aliases": "Bilal"},
        {"EmployeeID": "EMP011", "Name": "Usman", "Status": "Present", "RemainingLeaves": "20", "NextOffDay": "Friday", "Aliases": "Usman|EMP011"},
    ])

@st.cache_data(show_spinner=False)
def load_staff_data(file_path: str, mtime: float | None) -> pd.DataFrame:
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path, dtype=str).fillna("")
            missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
            if not missing:
                return df[REQUIRED_COLUMNS].copy()
        except Exception:
            pass
    return _demo_data()

def get_file_mtime(file_path: str):
    return os.path.getmtime(file_path) if os.path.exists(file_path) else None

def save_staff_data(uploaded_file) -> tuple[bool, str]:
    try:
        df = pd.read_csv(uploaded_file, dtype=str).fillna("")
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            return False, f"Missing columns: {missing}"
        df[REQUIRED_COLUMNS].to_csv(DATA_FILE, index=False)
        return True, f"Saved {len(df)} records successfully."
    except Exception as e:
        return False, f"Error: {e}"

def search_staff(df: pd.DataFrame, query: str) -> pd.DataFrame:
    if not query or not query.strip():
        return pd.DataFrame(columns=df.columns)
    q = query.strip().lower()

    def matches(row):
        if q in str(row["EmployeeID"]).lower() or q in str(row["Name"]).lower():
            return True
        aliases = [a.strip().lower() for a in str(row.get("Aliases", "")).split("|") if a.strip()]
        return any(q in a for a in aliases)

    return df[df.apply(matches, axis=1)]


# ============================================================
# SPEECH / VOICE OUTPUT
# ============================================================
def generate_speech(text: str, lang_code: str = "hi"):
    if not TTS_AVAILABLE:
        return None
    try:
        buf = io.BytesIO()
        gTTS(text=text, lang=lang_code).write_to_fp(buf)
        buf.seek(0)
        return buf
    except Exception:
        return None

def build_spoken_response(row, lang_choice: str) -> tuple[str, str]:
    name = row['Name']
    status = row['Status']
    leaves = row['RemainingLeaves']
    off_day = row['NextOffDay']

    if lang_choice == "Hindi / Urdu":
        text = f"Namaste {name}. Aapka status {status} hai. Aapke paas {leaves} chuttiyan baqi hain, aur agla off {off_day} ko hai."
        return text, "hi"
    else:
        text = f"Hello {name}. Your current status is {status}. You have {leaves} leaves remaining, and your next off day is {off_day}."
        return text, "en"

def get_status_class(status: str) -> str:
    s = str(status).lower()
    if "present" in s:
        return "status-present"
    if "leave" in s or "off" in s:
        return "status-leave"
    return "status-other"


# State variables
defaults = {
    "prefill_query": "",
    "reset_counter": 0,
    "input_source": None,
    "active_lang": "Hindi / Urdu",
    "result_shown_at": None,
    "last_shown_query": None,
    "admin_authenticated": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

inject_custom_css()

# Auto-reset logic
if st.session_state.result_shown_at and (time.time() - st.session_state.result_shown_at) > RESET_DELAY_SECONDS:
    st.session_state.prefill_query = ""
    st.session_state.reset_counter += 1
    st.session_state.result_shown_at = None
    st.session_state.last_shown_query = None
    st.session_state.input_source = None


# ============================================================
# ADMIN SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### 🔒 Kiosk Admin")
    if not st.session_state.admin_authenticated:
        with st.expander("Admin Login", expanded=False):
            pwd = st.text_input("Password", type="password", key="admin_pwd_box")
            if st.button("Unlock Admin", use_container_width=True):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect password")
    else:
        st.success("Admin Active")
        if st.button("Logout", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.rerun()

        st.divider()
        uploaded = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded and st.button("Save Data", use_container_width=True):
            ok, msg = save_staff_data(uploaded)
            if ok:
                st.success(msg)
                load_staff_data.clear()
                st.rerun()
            else:
                st.error(msg)

        st.divider()
        curr_df = load_staff_data(DATA_FILE, get_file_mtime(DATA_FILE))
        st.dataframe(curr_df, use_container_width=True, hide_index=True)


# ============================================================
# MAIN FOREGROUND VIEW
# ============================================================
staff_df = load_staff_data(DATA_FILE, get_file_mtime(DATA_FILE))

# 1. PXT HUB Title
st.markdown(f'<div class="pxt-title">{APP_TITLE}</div>', unsafe_allow_html=True)

# 2. Glowing Banner Video
st.markdown(
    f"""
    <div class="video-frame-wrap">
        <video autoplay loop muted playsinline>
            <source src="{VIDEO_URL}" type="video/mp4">
        </video>
    </div>
    """,
    unsafe_allow_html=True
)

# 3. Status Pill
if st.session_state.input_source == "voice":
    pill_text = f"Listening... Heard: {st.session_state.active_lang}"
elif st.session_state.input_source == "text":
    pill_text = "Searching Employee Record..."
else:
    pill_text = 'Listening... say "Hi PXT" or tap Speak'

st.markdown(
    f"""
    <div class="pill-wrapper">
        <span class="status-pill"><span class="status-dot"></span>{pill_text}</span>
    </div>
    """,
    unsafe_allow_html=True
)

# 4. Language Selector
selected_lang = st.radio(
    "Language",
    list(LANGUAGE_OPTIONS.keys()),
    horizontal=True,
    label_visibility="collapsed",
    key="lang_radio_select",
)
st.session_state.active_lang = selected_lang

# 5. Search Controls (Text input & Speak button)
reset_idx = st.session_state.reset_counter
col_input, col_speak = st.columns([4, 1])

with col_input:
    text_val = st.text_input(
        "Search Query",
        value=st.session_state.prefill_query,
        placeholder="Type a name, Employee ID, or speak...",
        label_visibility="collapsed",
        key=f"query_box_{reset_idx}",
    )

with col_speak:
    spoken_result = None
    if MIC_AVAILABLE:
        spoken_result = speech_to_text(
            language=LANGUAGE_OPTIONS[selected_lang],
            start_prompt="🎤 Speak",
            stop_prompt="⏹️ Done",
            just_once=True,
            use_container_width=True,
            key=f"mic_btn_{reset_idx}",
        )
    else:
        st.button("🎤 Speak", disabled=True, use_container_width=True)

# Input event triggers
if spoken_result:
    st.session_state.prefill_query = spoken_result
    st.session_state.input_source = "voice"
    st.session_state.reset_counter += 1
    st.rerun()

if text_val and text_val != st.session_state.prefill_query:
    st.session_state.prefill_query = text_val
    st.session_state.input_source = "text"
    st.rerun()


# 6. Results & Data Card Display
active_query = st.session_state.prefill_query
results = search_staff(staff_df, active_query) if (active_query and active_query.strip()) else pd.DataFrame()

if not results.empty:
    if st.session_state.last_shown_query != active_query:
        st.session_state.result_shown_at = time.time()
        st.session_state.last_shown_query = active_query

    staff_member = results.iloc[0]
    status_cls = get_status_class(staff_member["Status"])

    # Show Glass Card
    st.markdown(
        f"""
        <div class="result-card">
            <div class="card-name">{staff_member['Name']}</div>
            <div class="card-id">{staff_member['EmployeeID']}</div>
            <div class="stats-row">
                <div class="stat-box">
                    <div class="stat-lbl">STATUS</div>
                    <div class="stat-val {status_cls}">{staff_member['Status']}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-lbl">LEAVES LEFT</div>
                    <div class="stat-val">{staff_member['RemainingLeaves']}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-lbl">NEXT OFF DAY</div>
                    <div class="stat-val">{staff_member['NextOffDay']}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Voice Speech feedback
    if TTS_AVAILABLE:
        spoken_text, lang_tag = build_spoken_response(staff_member, st.session_state.active_lang)
        audio_buffer = generate_speech(spoken_text, lang_tag)
        if audio_buffer:
            st.audio(audio_buffer, format="audio/mp3", autoplay=True)

    if not st.session_state.admin_authenticated:
        inject_auto_reset(RESET_DELAY_SECONDS)

# 7. Helper Guidance text at the bottom
if results.empty:
    st.markdown(
        """
        <div class="guide-wrap">
            <div class="guide-main">I am your PXT AI Assistant</div>
            <div class="guide-sub">Say "Hi PXT" or enter an Employee ID / Name to get started</div>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        f"""
        <div class="guide-wrap">
            <div class="guide-main">Update for {results.iloc[0]['Name']}</div>
            <div class="guide-sub">Resetting screen in {RESET_DELAY_SECONDS} seconds...</div>
        </div>
        """,
        unsafe_allow_html=True
    )
