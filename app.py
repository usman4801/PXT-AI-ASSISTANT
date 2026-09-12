"""
PXT Hub - Hands-Free Voice Kiosk (Wake Word: "Hi PXT")
========================================================
Single-file Streamlit application for an Amazon-internal touchscreen
kiosk. Reads staff data from data.xlsx / data.csv, shows a full-screen
glassmorphism UI with a video background, and runs a fully hands-free
wake-word voice assistant using the browser's Web Speech API.

Deployment: Canopy / Streamlit Cloud / any container that can serve
this single app.py. No external HTML template files are used - all
frontend (HTML/CSS/JS) is embedded and rendered via
`streamlit.components.v1.html`.
"""

import json
import os

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ----------------------------------------------------------------------
# 0. APP CONFIG
# ----------------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_PASSWORD = "pxt123"  # NOTE: for production, move this to st.secrets

st.set_page_config(
    page_title="PXT Hub Kiosk",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------------------------------------------------------------
# 1. DATA FILE RESOLUTION
# ----------------------------------------------------------------------
def resolve_data_file() -> str:
    """data.xlsx ko priority deta hai, warna data.csv dhoondta hai."""
    xlsx_path = os.path.join(APP_DIR, "data.xlsx")
    csv_path = os.path.join(APP_DIR, "data.csv")
    if os.path.exists(xlsx_path):
        return xlsx_path
    if os.path.exists(csv_path):
        return csv_path
    return xlsx_path  # default path (even if it doesn't exist yet)


DATA_FILE_PATH = resolve_data_file()


# ----------------------------------------------------------------------
# 2. STAFF DATA LOADER
# ----------------------------------------------------------------------
def load_staff_data() -> list:
    """
    data.xlsx / data.csv se staff records load karta hai.
    Column names case/format mein thodi flexibility rakhi gayi hai
    (e.g. "EmployeeID" ya "Badge ID" dono chal jayenge).
    """
    if not os.path.exists(DATA_FILE_PATH):
        return []

    try:
        if DATA_FILE_PATH.endswith(".csv"):
            df = pd.read_csv(DATA_FILE_PATH, dtype=str).fillna("")
        else:
            df = pd.read_excel(DATA_FILE_PATH, dtype=str, engine="openpyxl").fillna("")

        records = []
        for _, row in df.iterrows():
            badge = str(row.get("EmployeeID", row.get("Badge ID", ""))).strip()
            if not badge or badge.lower() == "nan":
                continue
            records.append(
                {
                    "id": badge,
                    "name": str(row.get("Name", row.get("Employee Name", ""))).strip(),
                    "status": str(row.get("Status", row.get("Shift", ""))).strip(),
                    "leaves": str(row.get("RemainingLeaves", "")).strip(),
                    "next_off": str(row.get("NextOffDay", row.get("week off", ""))).strip(),
                    "alias": str(row.get("Aliases", "")).strip(),
                }
            )
        return records
    except Exception as e:
        st.sidebar.error(f"Data load error: {e}")
        return []


# ----------------------------------------------------------------------
# 3. ADMIN SIDEBAR (password-protected upload panel)
# ----------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🔒 PXT Admin")
    pwd = st.text_input("Password", type="password", placeholder="Admin password")

    if pwd:
        if pwd == ADMIN_PASSWORD:
            st.success("Access Granted")

            uploaded = st.file_uploader("Upload data.xlsx or data.csv", type=["xlsx", "csv"])
            if uploaded:
                try:
                    target_name = "data.xlsx" if uploaded.name.endswith(".xlsx") else "data.csv"
                    save_path = os.path.join(APP_DIR, target_name)
                    with open(save_path, "wb") as f:
                        f.write(uploaded.getbuffer())
                    st.success("Data uploaded successfully! Reloading...")
                    st.rerun()
                except Exception as e:
                    st.error(f"Upload failed: {e}")

            staff_preview = load_staff_data()
            st.caption(f"{len(staff_preview)} staff records loaded.")
            if staff_preview:
                st.dataframe(pd.DataFrame(staff_preview), use_container_width=True)
        else:
            st.error("Incorrect password")

# ----------------------------------------------------------------------
# 4. HIDE STREAMLIT CHROME (header, footer, menu, padding)
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
    #MainMenu, footer, header {display:none !important;}
    [data-testid="stToolbar"],
    [data-testid="stStatusWidget"],
    [data-testid="stDecoration"] {display:none !important;}
    div.block-container {padding: 0 !important; margin: 0 !important; max-width: 100% !important;}
    html, body, [data-testid="stAppViewContainer"] {background: #000000; overflow: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# 5. BUILD THE KIOSK FRONTEND (HTML + CSS + Web Speech API JS)
# ----------------------------------------------------------------------
staff_data = load_staff_data()
staff_json = json.dumps(staff_data, ensure_ascii=False)

kiosk_html_code = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, sans-serif; }}
    body, html {{ width: 100%; height: 100%; overflow: hidden; background: #05070c; }}

    #bgVideo {{
        position: fixed;
        right: 0; bottom: 0;
        min-width: 100%; min-height: 100%;
        width: auto; height: auto;
        z-index: 1;
        object-fit: cover;
        filter: brightness(0.4) contrast(1.1);
    }}

    .kiosk-overlay {{
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        z-index: 2;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: rgba(5, 7, 12, 0.35);
    }}

    .theme-switcher {{
        position: fixed;
        top: 25px; right: 30px;
        z-index: 10;
        display: flex;
        gap: 12px;
        background: rgba(0, 0, 0, 0.4);
        padding: 8px 14px;
        border-radius: 20px;
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.15);
    }}

    .theme-dot {{
        width: 14px; height: 14px;
        border-radius: 50%;
        cursor: pointer;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        border: 2px solid rgba(255, 255, 255, 0.7);
    }}
    .theme-dot:hover {{ transform: scale(1.3); }}
    .theme-dot.active {{ transform: scale(1.2); border-color: #ffffff; box-shadow: 0 0 10px #ffffff; }}

    .dot-theme1 {{ background: #0284c7; }}
    .dot-theme2 {{ background: #10b981; }}
    .dot-theme3 {{ background: #f59e0b; }}

    .card {{
        background: rgba(15, 23, 42, 0.78);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 24px;
        padding: 40px;
        width: 90%;
        max-width: 580px;
        text-align: center;
        box-shadow: 0 20px 50px rgba(0,0,0,0.6);
    }}

    h1 {{ font-size: 2.4rem; margin-bottom: 8px; color: #ffffff; letter-spacing: 0.5px; }}
    p.subtitle {{ color: #cbd5e1; margin-bottom: 25px; font-size: 1.1rem; }}

    .mic-indicator {{
        background: linear-gradient(135deg, #0284c7, #2563eb);
        border: none;
        width: 100px; height: 100px;
        border-radius: 50%;
        color: white;
        font-size: 2.8rem;
        margin: 0 auto 20px auto;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 25px rgba(2, 132, 199, 0.5);
        animation: pulse-blue 2s infinite;
    }}
    .mic-indicator.active-speech {{
        background: linear-gradient(135deg, #059669, #10b981);
        animation: pulse-green 1s infinite;
    }}

    @keyframes pulse-blue {{
        0% {{ box-shadow: 0 0 0 0 rgba(2, 132, 199, 0.6); }}
        70% {{ box-shadow: 0 0 0 20px rgba(2, 132, 199, 0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(2, 132, 199, 0); }}
    }}
    @keyframes pulse-green {{
        0% {{ box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.8); }}
        70% {{ box-shadow: 0 0 0 22px rgba(16, 185, 129, 0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }}
    }}

    .status {{ font-size: 1.25rem; color: #38bdf8; min-height: 32px; margin-bottom: 15px; font-weight: 600; }}

    .result-box {{
        background: rgba(30, 41, 59, 0.9);
        border-radius: 16px;
        padding: 22px;
        text-align: left;
        margin-top: 15px;
        display: none;
        border: 1px solid rgba(255, 255, 255, 0.12);
    }}
    .result-item {{
        font-size: 1.05rem;
        margin-bottom: 10px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 8px;
        color: #e2e8f0;
    }}
    .result-item:last-child {{ border: none; margin-bottom: 0; padding-bottom: 0; }}
    .highlight {{ color: #fbbf24; font-weight: 600; float: right; }}

    .not-found {{
        color: #f87171;
        font-weight: 600;
        margin-top: 12px;
        display: none;
    }}
</style>
</head>
<body>

<video autoplay muted loop playsinline id="bgVideo">
    <source src="banner.mp4" type="video/mp4">
</video>

<div class="theme-switcher">
    <div class="theme-dot dot-theme1 active" title="Theme 1" onclick="switchTheme('banner.mp4', this)"></div>
    <div class="theme-dot dot-theme2" title="Theme 2" onclick="switchTheme('banner2.mp4', this)"></div>
    <div class="theme-dot dot-theme3" title="Theme 3" onclick="switchTheme('banner3.mp4', this)"></div>
</div>

<div class="kiosk-overlay">
    <div class="card">
        <h1>🎙️ PXT Kiosk</h1>
        <p class="subtitle">Just say <b>"Hi PXT"</b> to wake up & check your shift</p>

        <div class="mic-indicator" id="micIcon">🎤</div>
        <div class="status" id="statusText">Starting microphone...</div>

        <div class="result-box" id="resultBox">
            <div class="result-item">👤 Name: <span class="highlight" id="resName">-</span></div>
            <div class="result-item">🆔 Badge ID: <span class="highlight" id="resId">-</span></div>
            <div class="result-item">📋 Shift / Status: <span class="highlight" id="resStatus">-</span></div>
            <div class="result-item">🌴 Remaining Leaves: <span class="highlight" id="resLeaves">-</span></div>
            <div class="result-item">📅 Next Off Day: <span class="highlight" id="resOff">-</span></div>
        </div>

        <div class="not-found" id="notFoundBox">Sorry, I couldn't find that employee. Please try again.</div>
    </div>
</div>

<script>
    const staffData = {staff_json};
    let recognition = null;
    let isAwake = false;
    let autoResetTimer = null;
    let restartTimer = null;
    let micStarted = false;

    // ---------------- Theme Switcher ----------------
    function switchTheme(videoSrc, dotElem) {{
        const video = document.getElementById('bgVideo');
        video.src = videoSrc;
        video.play().catch(() => {{}});
        document.querySelectorAll('.theme-dot').forEach(d => d.classList.remove('active'));
        dotElem.classList.add('active');
    }}

    // ---------------- Speech Recognition (self-healing) ----------------
    function startContinuousListening() {{
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {{
            document.getElementById('statusText').innerText =
                'Speech recognition not supported on this browser.';
            return;
        }}

        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = function () {{
            micStarted = true;
            document.getElementById('statusText').innerText =
                isAwake ? 'Listening for Name or Badge ID...' : 'Listening for "Hi PXT"...';
        }};

        recognition.onresult = function (event) {{
            let currentText = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {{
                currentText += event.results[i][0].transcript;
            }}
            currentText = currentText.trim().toLowerCase();
            if (currentText.length === 0) return;

            document.getElementById('micIcon').classList.add('active-speech');
            setTimeout(() => document.getElementById('micIcon').classList.remove('active-speech'), 800);

            const heardWakeWord =
                currentText.includes('hi pxt') ||
                currentText.includes('hey pxt') ||
                currentText.includes('pxt') ||
                currentText.includes('p x t');

            if (!isAwake && heardWakeWord) {{
                isAwake = true;
                document.getElementById('notFoundBox').style.display = 'none';
                document.getElementById('statusText').innerText = 'Awake! Say your Name or Badge ID...';
                speakResponse("Hi! Please state your name or badge ID.");
                return;
            }}

            if (isAwake) {{
                processVoiceQuery(currentText);
            }}
        }};

        recognition.onerror = function (event) {{
            console.log('Speech engine error, restarting:', event.error);
            safeRestart();
        }};

        recognition.onend = function () {{
            // Kiosk mode: always keep listening
            safeRestart();
        }};

        safeStart();
    }}

    function safeStart() {{
        try {{
            recognition.start();
        }} catch (e) {{
            // already started or transient error - retry shortly
            safeRestart();
        }}
    }}

    function safeRestart() {{
        clearTimeout(restartTimer);
        restartTimer = setTimeout(() => {{
            try {{ recognition.start(); }} catch (e) {{ /* ignore double-start */ }}
        }}, 600);
    }}

    // ---------------- Employee Lookup ----------------
    function processVoiceQuery(text) {{
        let query = text.replace('hi pxt', '').replace('hey pxt', '').replace('pxt', '').trim();
        if (query.length < 2) return;

        const found = staffData.find(emp =>
            (emp.id && query.includes(emp.id.toLowerCase())) ||
            (emp.name && query.includes(emp.name.toLowerCase())) ||
            (emp.alias && emp.alias.toLowerCase().split(',').some(a => a.trim() && query.includes(a.trim())))
        );

        if (found) {{
            showEmployeeDetails(found);
            speakResponse(
                "Hello " + found.name + ". Your status is " + found.status +
                " and your next off day is " + found.next_off + "."
            );
            document.getElementById('notFoundBox').style.display = 'none';
            scheduleAutoReset();
        }} else if (query.length > 4) {{
            // Enough speech captured but no match - let a couple more onresult events
            // arrive before giving up on this utterance.
            clearTimeout(autoResetTimer);
            autoResetTimer = setTimeout(() => {{
                document.getElementById('notFoundBox').style.display = 'block';
                speakResponse("Sorry, I could not find that employee. Please try again.");
                resetKioskToSleep();
            }}, 3000);
        }}
    }}

    function showEmployeeDetails(emp) {{
        document.getElementById('resName').innerText = emp.name || 'N/A';
        document.getElementById('resId').innerText = emp.id || 'N/A';
        document.getElementById('resStatus').innerText = emp.status || 'N/A';
        document.getElementById('resLeaves').innerText = emp.leaves || 'N/A';
        document.getElementById('resOff').innerText = emp.next_off || 'N/A';
        document.getElementById('resultBox').style.display = 'block';
        document.getElementById('statusText').innerText = 'Showing details for ' + emp.name;
    }}

    function scheduleAutoReset() {{
        clearTimeout(autoResetTimer);
        autoResetTimer = setTimeout(resetKioskToSleep, 8000);
    }}

    function resetKioskToSleep() {{
        isAwake = false;
        document.getElementById('resultBox').style.display = 'none';
        document.getElementById('notFoundBox').style.display = 'none';
        document.getElementById('statusText').innerText = 'Listening for "Hi PXT"...';
        document.getElementById('micIcon').classList.remove('active-speech');
    }}

    function speakResponse(text) {{
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.95;
            window.speechSynthesis.speak(utterance);
        }}
    }}

    // ---------------- Auto-start (hands-free, no click needed) ----------------
    window.addEventListener('load', () => {{
        // Most kiosk browsers (Chrome kiosk mode with --use-fake-ui-for-media-stream
        // or a granted mic permission policy) allow mic access without a user
        // gesture. If the browser blocks autostart, a single first tap anywhere
        // will kick it off as a fallback.
        startContinuousListening();
    }});
    document.body.addEventListener('click', () => {{
        if (!micStarted) startContinuousListening();
    }}, {{ once: true }});
</script>
</body>
</html>
"""

components.html(kiosk_html_code, height=900, scrolling=False)
