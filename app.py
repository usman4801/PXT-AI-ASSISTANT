"""
PXT Hub - AI Voice Assistant (Full Futuristic Kiosk)
A high-tech workplace kiosk featuring a seamless video avatar loop,
voice recognition, Hindi/Urdu voice feedback, and floating glassmorphic stats.
"""

from __future__ import annotations

import io
import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ---- Dependencies Check ----
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
RESET_DELAY_SECONDS = 7
VIDEO_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner.mp4"

LANGUAGE_OPTIONS = {
    "Hindi / Urdu": "hi-IN",
    "English": "en"
}

st.set_page_config(
    page_title=f"{APP_TITLE} - AI Voice Assistant",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# KIOSK STYLING & GLASSMORPHISM
# ============================================================
def inject_kiosk_css() -> None:
    st.markdown(
        """
        <style>
            /* Hide Streamlit Chrome */
            #MainMenu {visibility: hidden;}
            header[data-testid="stHeader"] {display: none;}
            footer {visibility: hidden;}
            div[data-testid="stToolbar"] {visibility: hidden; height: 0;}
            div[data-testid="stDecoration"] {display: none;}
            div[data-testid="stStatusWidget"] {visibility: hidden;}
            [data-testid="collapsedControl"] {opacity: 0.3; transition: opacity .2s ease;}
            [data-testid="collapsedControl"]:hover {opacity: 1;}

            /* Kiosk Fullscreen Dark Universe */
            html, body, [data-testid="stAppViewContainer"], .stApp {
                background: radial-gradient(circle at 50% 15%, #0d1222 0%, #05070d 60%, #020305 100%) !important;
                color: #e9edf5;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
                overflow-x: hidden;
            }
            .block-container {
                padding-top: 1.5rem !important;
                padding-bottom: 1.5rem !important;
                max-width: 820px !important;
                margin: 0 auto;
            }

            /* Top Pill Indicator */
            .status-pill-wrap {
                text-align: center;
                margin-bottom: 0.8rem;
            }
            .status-pill {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 0.4rem 1.3rem;
                border-radius: 999px;
                background: rgba(14, 23, 42, 0.7);
                border: 1px solid rgba(126, 224, 255, 0.25);
                box-shadow: 0 0 15px rgba(59, 130, 246, 0.2);
                font-size: 0.85rem;
                font-weight: 600;
                color: #93c5fd;
                letter-spacing: 0.04em;
                backdrop-filter: blur(8px);
            }
            .status-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #38bdf8;
                box-shadow: 0 0 8px #38bdf8;
                animation: pulseDot 1.4s infinite ease-in-out;
            }
            @keyframes pulseDot {
                0%, 100% { transform: scale(1); opacity: 0.7; }
                50% { transform: scale(1.4); opacity: 1; }
            }

            /* Holographic Avatar Stage */
            .avatar-stage {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 1.2rem;
                margin: 0.2rem 0 1.2rem 0;
            }
            .eq-side {
                display: flex;
                align-items: center;
                gap: 5px;
                height: 140px;
            }
            .eq-bar {
                width: 5px;
                border-radius: 6px;
                animation: eqPulse 1.2s infinite ease-in-out;
            }
            .eq-left .eq-bar { background: linear-gradient(180deg, #38bdf8, #6366f1); }
            .eq-right .eq-bar { background: linear-gradient(180deg, #ec4899, #8b5cf6); }

            @keyframes eqPulse {
                0%, 100% { transform: scaleY(0.25); opacity: 0.4; }
                50% { transform: scaleY(1); opacity: 1; }
            }

            .avatar-portal {
                position: relative;
                width: 250px;
                height: 250px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .portal-video {
                width: 220px;
                height: 220px;
                border-radius: 50%;
                object-fit: cover;
                border: 2px solid rgba(126, 224, 255, 0.4);
                box-shadow: 0 0 35px rgba(56, 189, 248, 0.35), inset 0 0 20px rgba(0,0,0,0.8);
                z-index: 2;
                background: #000;
            }
            .glow-ring {
                position: absolute;
                border-radius: 50%;
                border: 2px solid transparent;
            }
            .ring-a {
                width: 248px;
                height: 248px;
                border-top-color: rgba(56, 189, 248, 0.8);
                border-right-color: rgba(168, 85, 247, 0.6);
                animation: spinPortal 8s linear infinite;
            }
            .ring-b {
                width: 236px;
                height: 236px;
                border-bottom-color: rgba(236, 72, 153, 0.8);
                border-left-color: rgba(56, 189, 248, 0.5);
                animation: spinPortal 11s linear infinite reverse;
            }
            @keyframes spinPortal {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }

            .portal-badge {
                position: absolute;
                bottom: 2px;
                z-index: 4;
                background: rgba(3, 7, 18, 0.85);
                border: 1px solid rgba(126, 224, 255, 0.4);
                padding: 0.15rem 0.9rem;
                border-radius: 999px;
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.3em;
                color: #f1f5f9;
                text-shadow: 0 0 8px rgba(56, 189, 248, 0.8);
            }

            /* Futuristic Floating Card */
            .holo-card {
                background: rgba(15, 23, 42, 0.65);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid rgba(126, 224, 255, 0.22);
                border-radius: 22px;
                padding: 1.5rem 1.8rem;
                margin: 0.5rem auto 1.2rem auto;
                max-width: 480px;
                box-shadow: 0 15px 40px rgba(0, 0, 0, 0.6), 0 0 25px rgba(56, 189, 248, 0.15);
                text-align: center;
                animation: floatUp 0.4s ease-out;
            }
            @keyframes floatUp {
                from { opacity: 0; transform: translateY(14px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .holo-card-name {
                font-size: 1.7rem;
                font-weight: 800;
                color: #ffffff;
                letter-spacing: -0.02em;
            }
            .holo-card-id {
                color: #94a3b8;
                font-size: 0.85rem;
                margin-bottom: 1.1rem;
                letter-spacing: 0.05em;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 0.7rem;
            }
            .stat-box {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
                padding: 0.75rem 0.4rem;
            }
            .stat-label {
                font-size: 0.64rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: #94a3b8;
                margin-bottom: 0.25rem;
            }
            .stat-val {
                font-size: 1.08rem;
                font-weight: 700;
            }
            .status-present { color: #34d399; text-shadow: 0 0 10px rgba(52, 211, 153, 0.4); }
            .status-leave { color: #fb923c; text-shadow: 0 0 10px rgba(251, 146, 60, 0.4); }
            .status-other { color: #38bdf8; }

            /* Guidance Subtitles */
            .guide-wrap {
                text-align: center;
                margin-bottom: 1.2rem;
            }
            .guide-main {
                font-size: 1.05rem;
                font-weight: 700;
                color: #f8fafc;
            }
            .guide-sub {
                font-size: 0.82rem;
                color: #64748b;
                margin-top: 0.2rem;
            }

            /* Custom Inputs & Controls */
            div[data-testid="stTextInput"] input {
                background: rgba(15, 23, 42, 0.7) !important;
                border: 1px solid rgba(126, 224, 255, 0.2) !important;
                border-radius: 16px !important;
                color: #fff !important;
                height: 3.2rem;
                font-size: 1rem !important;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            }
            div[data-testid="stTextInput"] input:focus {
                border-color: #38bdf8 !important;
                box-shadow: 0 0 14px rgba(56, 189, 248, 0.3) !important;
            }
            .stButton > button {
                background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                color: #f8fafc;
                border: 1px solid rgba(126, 224, 255, 0.25);
                border-radius: 16px;
                height: 3.2rem;
                font-weight: 600;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            }
            .stButton > button:hover {
                border-color: #38bdf8;
                color: #38bdf8;
                box-shadow: 0 0 15px rgba(56, 189, 248, 0.25);
            }

            /* Radio Buttons Centered */
            div[role="radiogroup"] {
                justify-content: center;
                margin-bottom: 0.6rem;
            }

            /* Audio Player Cleanup */
            audio {
                width: 100%;
                margin-top: 0.6rem;
                border-radius: 12px;
                opacity: 0.85;
            }

            .footer-info {
                text-align: center;
                color: #475569;
                font-size: 0.74rem;
                margin-top: 1.8rem;
                letter-spacing: 0.04em;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_avatar_portal() -> None:
    """Renders the circular video avatar loop flanked by dynamic equalizer bars."""
    def make_bars(side: str, count: int = 12) -> str:
        items = []
        for i in range(count):
            duration = 0.6 + (i % 4) * 0.18
            delay = (i % 6) * 0.09
            height = 32 + (i % 5) * 16
            items.append(
                f'<span class="eq-bar" style="animation-duration:{duration}s;'
                f'animation-delay:{delay}s;height:{height}%;"></span>'
            )
        return f'<div class="eq-side eq-{side}">{"".join(items)}</div>'

    st.markdown(
        f"""
        <div class="avatar-stage">
            {make_bars("left")}
            <div class="avatar-portal">
                <div class="glow-ring ring-a"></div>
                <div class="glow-ring ring-b"></div>
                <video class="portal-video" src="{VIDEO_URL}" autoplay loop muted playsinline></video>
                <div class="portal-badge">{APP_TITLE}</div>
            </div>
            {make_bars("right")}
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_auto_reset(delay_seconds: float) -> None:
    """Resets the kiosk display automatically after inactivity."""
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
# DATA ENGINE
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
# VOICE OUTPUT (HINDI / URDU / ENGLISH)
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
    """Generates natural bilingual audio replies for the assistant."""
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

def get_status_style(status: str) -> str:
    s = str(status).lower()
    if "present" in s:
        return "status-present"
    if "leave" in s or "off" in s:
        return "status-leave"
    return "status-other"


# ============================================================
# STATE INITIALIZATION
# ============================================================
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

inject_kiosk_css()

# Auto reset timer trigger
if st.session_state.result_shown_at and (time.time() - st.session_state.result_shown_at) > RESET_DELAY_SECONDS:
    st.session_state.prefill_query = ""
    st.session_state.reset_counter += 1
    st.session_state.result_shown_at = None
    st.session_state.last_shown_query = None
    st.session_state.input_source = None


# ============================================================
# ADMIN DRAWER (SIDEBAR)
# ============================================================
with st.sidebar:
    st.markdown("### 🔒 PXT Kiosk Administration")
    if not st.session_state.admin_authenticated:
        with st.expander("Admin Login", expanded=False):
            pwd = st.text_input("Password", type="password", key="admin_pwd_box")
            if st.button("Unlock Admin", use_container_width=True):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid password")
    else:
        st.success("Admin unlocked")
        if st.button("Lock Admin", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.rerun()

        st.divider()
        st.markdown("**Upload Updated Staff Sheet**")
        uploaded = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded and st.button("Overwrite staff_data.csv", use_container_width=True):
            ok, msg = save_staff_data(uploaded)
            if ok:
                st.success(msg)
                load_staff_data.clear()
                st.rerun()
            else:
                st.error(msg)

        st.divider()
        st.markdown("**Live Database Preview**")
        curr_df = load_staff_data(DATA_FILE, get_file_mtime(DATA_FILE))
        st.dataframe(curr_df, use_container_width=True, hide_index=True)


# ============================================================
# MAIN KIOSK VIEW
# ============================================================
staff_df = load_staff_data(DATA_FILE, get_file_mtime(DATA_FILE))

# 1. Top Status Pill
if st.session_state.input_source == "voice":
    pill_msg = f"Listening... Heard: {st.session_state.active_lang}"
elif st.session_state.input_source == "text":
    pill_msg = "Processing Search Query"
else:
    pill_msg = 'Listening... Say "Hi PXT" or tap Speak'

st.markdown(
    f'''<div class="status-pill-wrap">
        <span class="status-pill"><span class="status-dot"></span>{pill_msg}</span>
    </div>''',
    unsafe_allow_html=True
)

# 2. Portal Video Avatar
render_avatar_portal()

# 3. Language Selector & Input Interface
reset_idx = st.session_state.reset_counter

selected_lang = st.radio(
    "Language",
    list(LANGUAGE_OPTIONS.keys()),
    horizontal=True,
    label_visibility="collapsed",
    key="lang_radio_select",
)
st.session_state.active_lang = selected_lang

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
        st.button("🎤 Speak", disabled=True, use_container_width=True, help="Install streamlit-mic-recorder")

if spoken_result:
    st.session_state.prefill_query = spoken_result
    st.session_state.input_source = "voice"
    st.session_state.reset_counter += 1
    st.rerun()

current_query = text_val
if current_query and current_query != st.session_state.prefill_query:
    st.session_state.input_source = "text"
elif not current_query:
    st.session_state.input_source = None


# ============================================================
# RESULTS DISPLAY & AUTO-RESET
# ============================================================
if current_query and current_query.strip():
    records = search_staff(staff_df, current_query)

    if records.empty:
        st.session_state.result_shown_at = None
        st.session_state.last_shown_query = None
        st.markdown(
            f'''<div class="guide-wrap">
                <div class="guide-main">Record not found</div>
                <div class="guide-sub">No results for "{current_query}". Please try again.</div>
            </div>''',
            unsafe_allow_html=True
        )
    else:
        if st.session_state.last_shown_query != current_query:
            st.session_state.result_shown_at = time.time()
            st.session_state.last_shown_query = current_query

        staff_member = records.iloc[0]
        stat_color_cls = get_status_style(staff_member["Status"])

        # Holographic Glass Card
        st.markdown(
            f"""
            <div class="holo-card">
                <div class="holo-card-name">{staff_member['Name']}</div>
                <div class="holo-card-id">{staff_member['EmployeeID']}</div>
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-label">STATUS</div>
                        <div class="stat-val {stat_color_cls}">{staff_member['Status']}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">LEAVES LEFT</div>
                        <div class="stat-val">{staff_member['RemainingLeaves']}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">NEXT OFF DAY</div>
                        <div class="stat-val">{staff_member['NextOffDay']}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f'''<div class="guide-wrap">
                <div class="guide-main">Update for {staff_member["Name"]}</div>
                <div class="guide-sub">Screen auto-resetting in {RESET_DELAY_SECONDS} seconds...</div>
            </div>''',
            unsafe_allow_html=True
        )

        # Spoken audio response
        if TTS_AVAILABLE:
            spoken_text, lang_tag = build_spoken_response(staff_member, selected_lang)
            audio_buffer = generate_speech(spoken_text, lang_tag)
            if audio_buffer:
                st.audio(audio_buffer, format="audio/mp3", autoplay=True)

        # Trigger auto-reset
        if not st.session_state.admin_authenticated:
            inject_auto_reset(RESET_DELAY_SECONDS)

else:
    st.session_state.result_shown_at = None
    st.session_state.last_shown_query = None
    st.markdown(
        """
        <div class="guide-wrap">
            <div class="guide-main">I am your PXT AI Assistant</div>
            <div class="guide-sub">Tap "Speak" or type an Employee ID / Name to begin</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown(
    f'<div class="footer-info">PXT Hub · Live Kiosk · {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>',
    unsafe_allow_html=True
)
