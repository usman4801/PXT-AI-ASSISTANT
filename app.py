"""
PXT Hub - AI Voice Assistant
A workplace kiosk dashboard for staff attendance/leave lookup with voice search
and an admin panel for CSV-based data management.
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
APP_TITLE = "PXT Hub - AI Voice Assistant"
DATA_FILE = "staff_data.csv"
ADMIN_PASSWORD = "pxt123"
BANNER_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner.mp4"
REQUIRED_COLUMNS = ["EmployeeID", "Name", "Status", "RemainingLeaves", "NextOffDay", "Aliases"]

st.set_page_config(page_title=APP_TITLE, page_icon="🎙️", layout="wide")


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


# ============================================================
# SESSION STATE
# ============================================================
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False


# ============================================================
# SIDEBAR - ADMIN PANEL
# ============================================================
with st.sidebar:
    st.header("🔐 Admin Panel")

    if not st.session_state.admin_authenticated:
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
        st.subheader("Upload updated staff CSV")
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
        st.subheader("Current dataset preview")
        current_df = load_staff_data(DATA_FILE, get_file_mtime(DATA_FILE))
        st.dataframe(current_df, use_container_width=True, hide_index=True)
        st.caption(f"{len(current_df)} record(s) loaded.")


# ============================================================
# MAIN PAGE - BANNER
# ============================================================
st.title(APP_TITLE)

try:
    st.video(BANNER_URL)
except Exception:
    st.info("Banner video is currently unavailable.")

st.divider()


# ============================================================
# MAIN PAGE - SEARCH
# ============================================================
st.subheader("🔍 Find a colleague")
st.caption("Search by name, employee ID, or known alias — by typing or speaking.")

staff_df = load_staff_data(DATA_FILE, get_file_mtime(DATA_FILE))

col_text, col_mic = st.columns([5, 1])

with col_text:
    text_query = st.text_input(
        "Search",
        value=st.session_state.search_query,
        placeholder="e.g. Ayesha, EMP001, or an alias",
        label_visibility="collapsed",
        key="text_query_input",
    )

with col_mic:
    voice_text = None
    if MIC_AVAILABLE:
        voice_text = speech_to_text(
            language="en",
            start_prompt="🎤",
            stop_prompt="⏹️",
            just_once=True,
            use_container_width=True,
            key="mic_recorder",
        )
    else:
        st.button("🎤", disabled=True, help="Install streamlit-mic-recorder to enable voice input")

# Voice input takes priority and auto-populates + triggers the search
active_query = text_query
if voice_text:
    active_query = voice_text
    st.session_state.search_query = voice_text
    st.rerun()

st.divider()


# ============================================================
# MAIN PAGE - RESULTS
# ============================================================
if active_query and active_query.strip():
    results = search_staff(staff_df, active_query)

    if results.empty:
        st.warning(f"No staff record found matching **'{active_query}'**.")
    else:
        st.success(f"Found {len(results)} matching record(s).")

        for _, row in results.iterrows():
            with st.container(border=True):
                st.markdown(f"### {row['Name']}")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Employee ID", row["EmployeeID"])
                c2.metric("Status", row["Status"])
                c3.metric("Remaining Leaves", row["RemainingLeaves"])
                c4.metric("Next Off Day", row["NextOffDay"])

                if TTS_AVAILABLE:
                    speech_text = build_speech_text(row)
                    audio_buf = generate_speech(speech_text)
                    if audio_buf is not None:
                        st.audio(audio_buf, format="audio/mp3")
                else:
                    st.caption("Install `gTTS` to enable spoken confirmations.")
else:
    st.info("Type a name/ID above or tap the microphone to search for a colleague.")


# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption(f"PXT Hub · Data last checked {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
