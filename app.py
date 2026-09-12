"""
PXT HUB - Clean Cyber Kiosk with Real-Time Audio Detection & Speech Recognition
Restored from user's original working build. Minimum changes for Canopy compliance
+ S3 banner fetch + sandbox-safe navigation.
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

# S3 (Canopy Storage) — all via env vars, no hardcoded secrets
S3_BUCKET   = os.environ.get("PXT_S3_BUCKET",   "")
S3_PREFIX   = os.environ.get("PXT_S3_PREFIX",   "")
S3_BANNER_1 = os.environ.get("PXT_BANNER_1_KEY", "banner.mp4")
S3_BANNER_2 = os.environ.get("PXT_BANNER_2_KEY", "banner2.mp4")
S3_DATA_KEY = os.environ.get("PXT_DATA_KEY",     "staff_data.csv")

# Local dev fallback — use Streamlit static folder (banner.mp4 in /static)
LOCAL_BANNER_1 = "app/static/banner.mp4"
LOCAL_BANNER_2 = "app/static/banner2.mp4"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# S3 HELPERS
# ============================================================
try:
    import boto3
    _BOTO_OK = True
except ImportError:
    _BOTO_OK = False


@st.cache_resource(show_spinner=False)
def _s3_client():
    if not _BOTO_OK or not S3_BUCKET:
        return None
    try:
        return boto3.client("s3")
    except Exception:
        return None


@st.cache_data(ttl=1800, show_spinner=False)
def s3_presigned_url(key: str, local_fallback: str) -> str:
    s3 = _s3_client()
    if s3 is None or not S3_BUCKET:
        return local_fallback  # local dev — Streamlit static file
    try:
        full_key = f"{S3_PREFIX}/{key}" if S3_PREFIX else key
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": full_key},
            ExpiresIn=3600,
        )
    except Exception:
        return local_fallback


@st.cache_data(ttl=600, show_spinner=False)
def s3_load_csv(key: str):
    s3 = _s3_client()
    if s3 is None or not S3_BUCKET:
        return None
    try:
        full_key = f"{S3_PREFIX}/{key}" if S3_PREFIX else key
        obj = s3.get_object(Bucket=S3_BUCKET, Key=full_key)
        return pd.read_csv(obj["Body"], dtype=str).fillna("")
    except Exception:
        return None


# Session state
st.session_state.setdefault("active_banner", 1)
st.session_state.setdefault("kiosk_state", "idle")
st.session_state.setdefault("current_employee", None)
st.session_state.setdefault("last_heard", "")
st.session_state.setdefault("last_interaction", None)

# Banner switch
if "switch_banner" in st.query_params:
    st.session_state.active_banner = 2 if st.session_state.active_banner == 1 else 1
    del st.query_params["switch_banner"]
    st.rerun()

# Voice payload arrival
if "voice_payload" in st.query_params:
    spoken_val = str(st.query_params["voice_payload"]).strip()
    del st.query_params["voice_payload"]
    st.session_state["last_interaction"] = time.time()
    cs = st.session_state.get("kiosk_state", "idle")
    if cs == "idle":
        st.session_state["kiosk_state"] = "asked_badge"
        st.session_state["last_heard"] = ""
    else:
        st.session_state["last_heard"] = spoken_val
    st.rerun()

banner1_url = s3_presigned_url(S3_BANNER_1, LOCAL_BANNER_1)
banner2_url = s3_presigned_url(S3_BANNER_2, LOCAL_BANNER_2)
active_video = banner1_url if st.session_state.active_banner == 1 else banner2_url


# ============================================================
# DATA
# ============================================================
def load_data():
    df = s3_load_csv(S3_DATA_KEY)
    if df is not None and not df.empty:
        return df
    if os.path.exists(DATA_FILE):
        try:
            return pd.read_csv(DATA_FILE, dtype=str).fillna("")
        except Exception:
            pass
    return pd.DataFrame([
        {"EmployeeID": "EMP001", "Name": "Ayesha Khan", "Status": "Present",  "RemainingLeaves": "12", "NextOffDay": "Saturday"},
        {"EmployeeID": "EMP002", "Name": "Bilal Ahmed", "Status": "On Leave", "RemainingLeaves": "5",  "NextOffDay": "Sunday"},
        {"EmployeeID": "EMP011", "Name": "Usman",       "Status": "Present",  "RemainingLeaves": "20", "NextOffDay": "Friday"},
    ])


def answer_employee_question(emp, question: str) -> str:
    q = question.lower()
    name = emp["Name"]
    if "leave" in q or "remaining" in q or "vacation" in q:
        return f"{name}, you have {emp['RemainingLeaves']} remaining leaves."
    elif "off" in q or "holiday" in q or "weekend" in q:
        return f"{name}, your next off day is on {emp['NextOffDay']}."
    elif "status" in q or "present" in q or "absent" in q:
        return f"{name}, your current status is {emp['Status']}."
    return f"{name}, status: {emp['Status']}, leaves: {emp['RemainingLeaves']}, next off: {emp['NextOffDay']}."


staff_df = load_data()

# Auto reset
last_act = st.session_state.get("last_interaction")
if last_act and (time.time() - last_act > RESET_DELAY):
    st.session_state["kiosk_state"] = "idle"
    st.session_state["current_employee"] = None
    st.session_state["last_interaction"] = None
    st.session_state["last_heard"] = ""
    st.rerun()

# ============================================================
# CSS (unchanged from original; system font stack instead of CDN)
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
            margin: 0 !important; padding: 0 !important;
            overflow: hidden !important;
            height: 100vh !important; width: 100vw !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }

        .main .block-container { padding: 0 !important; margin: 0 !important; max-width: 100vw !important; width: 100vw !important; height: 100vh !important; }

        #kiosk-bg-video { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; object-fit: cover; z-index: 0 !important; pointer-events: none !important; }

        .hud-title-wrap { position: fixed; top: 8vh; left: 50%; transform: translateX(-50%); z-index: 30; text-align: center; pointer-events: none; }
        .hud-pxt-title { font-size: 1.6rem !important; font-weight: 800; letter-spacing: 0.25em; color: #ffffff; text-shadow: 0 0 16px rgba(56,189,248,0.9), 0 0 30px rgba(56,189,248,0.5); text-transform: uppercase; }

        .theme-dot-anchor { position: fixed; top: 20px; right: 25px; width: 16px; height: 16px; background: #38bdf8; border: 2px solid #fff; border-radius: 50%; box-shadow: 0 0 12px #38bdf8; z-index: 99999; cursor: pointer; display: block; }

        .top-hud { position: fixed; top: 20px; left: 20px; display: flex; align-items: center; gap: 10px; z-index: 999999; background: rgba(10,15,30,0.65); padding: 8px 16px; border-radius: 20px; border: 1px solid rgba(56,189,248,0.3); backdrop-filter: blur(8px); }
        .dot { width: 12px; height: 12px; border-radius: 50%; background: #f59e0b; box-shadow: 0 0 8px #f59e0b, 0 0 16px rgba(245,158,11,0.6); transition: background 0.3s ease, box-shadow 0.3s ease; }
        .dot.listening { background: #00e5ff !important; box-shadow: 0 0 12px #00e5ff, 0 0 24px #00e5ff !important; animation: dotPulse 1s infinite alternate; }
        @keyframes dotPulse { from { transform: scale(0.85); opacity: 0.8; } to { transform: scale(1.35); opacity: 1; } }
        .status-txt { font-size: 12px; font-weight: 700; letter-spacing: 0.08em; color: #fbbf24; text-transform: uppercase; }
        .status-txt.listening { color: #00e5ff !important; }

        /* Mic picker (startup + always-visible so user can change any time) */
        .mic-picker { position: fixed; top: 60px; left: 20px; z-index: 999998; background: rgba(10,15,30,0.85); border: 1px solid rgba(56,189,248,0.35); border-radius: 12px; padding: 8px 12px; font-size: 11px; color: #7dd3fc; backdrop-filter: blur(10px); }
        .mic-picker select { background: #0f172a; color: #38bdf8; border: 1px solid rgba(56,189,248,0.4); border-radius: 4px; padding: 3px 6px; font-size: 11px; max-width: 260px; }
        .mic-heard { position: fixed; top: 105px; left: 20px; z-index: 999998; background: rgba(15,23,42,0.85); border: 1px solid rgba(125,211,252,0.35); border-radius: 8px; padding: 6px 12px; font-size: 12px; font-family: monospace; color: #7dd3fc; max-width: 400px; }
        .recog-status { position: fixed; top: 145px; left: 20px; z-index: 999998; background: rgba(15,23,42,0.85); border: 1px solid rgba(125,211,252,0.35); border-radius: 8px; padding: 6px 12px; font-size: 12px; font-family: monospace; color: #fbbf24; max-width: 400px; }

        .hologram-stage { position: fixed; top: 46%; left: 50%; transform: translate(-50%, -50%); display: flex; align-items: center; justify-content: center; gap: 48px; z-index: 5; pointer-events: none !important; }
        .wave-col { display: flex; align-items: center; gap: 6px; height: 130px; }
        .wave-col span { display: block; width: 5px; height: 18%; border-radius: 3px; background: linear-gradient(180deg, #7dd3fc, #0ea5e9); box-shadow: 0 0 8px rgba(56,189,248,0.7); animation: waveBounce 1.6s ease-in-out infinite; }
        .wave-col span:nth-child(1) { animation-delay: 0.0s; }
        .wave-col span:nth-child(2) { animation-delay: 0.15s; }
        .wave-col span:nth-child(3) { animation-delay: 0.3s; }
        .wave-col span:nth-child(4) { animation-delay: 0.45s; }
        .wave-col span:nth-child(5) { animation-delay: 0.3s; }
        .wave-col span:nth-child(6) { animation-delay: 0.15s; }
        .wave-col span:nth-child(7) { animation-delay: 0.0s; }
        .wave-col span:nth-child(8) { animation-delay: 0.2s; }
        @keyframes waveBounce { 0%,100% { height: 12%; } 50% { height: 90%; } }
        .hologram-stage.listening .wave-col span { animation-duration: 0.65s; }

        .ai-face { position: relative; width: 190px; height: 190px; display: flex; align-items: center; justify-content: center; }
        .face-ring { position: absolute; border-radius: 50%; border: 1.5px solid rgba(56,189,248,0.35); animation: ringSpin 7s linear infinite; }
        .ring-outer { width: 190px; height: 190px; border-color: rgba(56,189,248,0.22); }
        .ring-mid { width: 148px; height: 148px; border-color: rgba(56,189,248,0.45); animation-direction: reverse; animation-duration: 4.5s; }
        @keyframes ringSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .hologram-stage.listening .ring-outer, .hologram-stage.listening .ring-mid { animation-duration: 1.6s; }

        .face-core { width: 112px; height: 112px; border-radius: 50%; background: radial-gradient(circle at 35% 30%, rgba(186,230,253,0.95), rgba(14,116,144,0.45) 55%, rgba(8,20,35,0.92) 100%); box-shadow: 0 0 30px rgba(56,189,248,0.55), 0 0 60px rgba(56,189,248,0.3), inset 0 0 20px rgba(255,255,255,0.15); display: flex; align-items: center; justify-content: center; animation: coreGlow 3s ease-in-out infinite; }
        @keyframes coreGlow { 0%,100% { box-shadow: 0 0 30px rgba(56,189,248,0.5), 0 0 60px rgba(56,189,248,0.25); } 50% { box-shadow: 0 0 46px rgba(56,189,248,0.9), 0 0 92px rgba(56,189,248,0.42); } }
        .hologram-stage.listening .face-core { animation-duration: 0.9s; }
        .face-core-inner { width: 44px; height: 44px; border-radius: 50%; background: radial-gradient(circle at 40% 35%, rgba(255,255,255,0.95), rgba(224,247,255,0.15) 70%, transparent 100%); filter: drop-shadow(0 0 10px #7dd3fc); }

        #actionPill { position: fixed !important; bottom: 5vh !important; left: 50% !important; transform: translateX(-50%) !important; z-index: 999999999 !important; background: rgba(15,23,42,0.92) !important; border: 1.5px solid rgba(56,189,248,0.6) !important; border-radius: 30px !important; padding: 13px 32px !important; color: #38bdf8 !important; font-size: 15px !important; font-weight: 700 !important; letter-spacing: 0.04em !important; backdrop-filter: blur(12px) !important; box-shadow: 0 8px 30px rgba(0,0,0,0.7) !important; cursor: pointer !important; user-select: none !important; transition: all 0.25s ease !important; display: inline-block !important; }
        #actionPill:hover { color: #fff !important; border-color: #00e5ff !important; box-shadow: 0 0 24px rgba(0,229,255,0.55) !important; transform: translateX(-50%) scale(1.03) !important; }
        #actionPill.listening { color: #00e5ff !important; border-color: rgba(0,229,255,0.8) !important; box-shadow: 0 0 22px rgba(0,229,255,0.45) !important; }

        .kiosk-ui-container { position: fixed !important; bottom: 14vh !important; left: 50% !important; transform: translateX(-50%) !important; z-index: 9999999 !important; width: 90% !important; max-width: 480px !important; display: flex !important; flex-direction: column !important; align-items: center !important; gap: 12px !important; }
        .employee-glass-card { background: rgba(11,15,25,0.88); backdrop-filter: blur(25px); border: 1.5px solid rgba(56,189,248,0.45); border-radius: 18px; padding: 1.1rem 1.4rem; width: 100%; text-align: center; box-shadow: 0 15px 40px rgba(0,0,0,0.8); }
        .emp-name { font-size: 1.35rem; font-weight: 800; color: #fff; }
        .emp-badge { color: #38bdf8; font-size: 0.85rem; margin-bottom: 0.7rem; }
        .emp-stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
        .emp-stat-box { background: rgba(255,255,255,0.05); border-radius: 10px; padding: 0.5rem 0.2rem; }
        .emp-stat-lbl { font-size: 0.62rem; color: #94a3b8; text-transform: uppercase; }
        .emp-stat-val { font-size: 1.05rem; font-weight: 700; margin-top: 2px; }
        .status-present { color: #34d399; }
        .status-leave { color: #fb923c; }

        div[data-testid="stTextInput"] input { background: rgba(15,23,42,0.9) !important; border: 1.5px solid rgba(56,189,248,0.45) !important; border-radius: 14px !important; color: #fff !important; height: 3rem; text-align: center; }
    </style>
    """,
    unsafe_allow_html=True,
)

current_state = st.session_state.get("kiosk_state", "idle")
current_emp = st.session_state.get("current_employee")

pill_initial_text = 'Say "Hi PXT" or Click here' if current_state == "idle" else 'Speak or Type below'

video_source_html = f'<source src="{active_video}" type="video/mp4">' if active_video else ""

# Render Background, Hologram, Pill, Mic Picker, Heard box
st.markdown(
    f"""
    <video id="kiosk-bg-video" autoplay loop muted playsinline>
        {video_source_html}
    </video>

    <div class="hud-title-wrap"><div class="hud-pxt-title">{APP_TITLE}</div></div>
    <a href="?switch_banner=true" target="_self" class="theme-dot-anchor" title="Switch Theme"></a>

    <div id="topHud" class="top-hud">
        <div id="micDot" class="dot"></div>
        <div id="statusLabel" class="status-txt">STANDBY</div>
    </div>

    <div class="mic-picker">
        Mic: <select id="micDeviceSelect"><option value="">Detecting...</option></select>
    </div>
    <div id="micHeard" class="mic-heard">HEARD: (waiting for speech)</div>
    <div id="recogStatus" class="recog-status">RECOGNITION: starting…</div>

    <div id="hologramStage" class="hologram-stage">
        <div class="wave-col wave-left"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>
        <div class="ai-face">
            <div class="face-ring ring-outer"></div>
            <div class="face-ring ring-mid"></div>
            <div class="face-core"><div class="face-core-inner"></div></div>
        </div>
        <div class="wave-col wave-right"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>
    </div>

    <div id="actionPill">{pill_initial_text}</div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# JS BRIDGE — RESTORED FROM ORIGINAL WORKING BUILD
# Only diff: sendPayload uses parent-DOM <a> click (sandbox-safe)
# ============================================================
speak_text = ""
if current_state == "asked_badge" and not st.session_state.get("last_heard"):
    speak_text = "Please say or enter your badge number."
elif current_state == "employee_active" and current_emp is not None and not st.session_state.get("last_heard"):
    speak_text = f"Welcome {current_emp['Name']}. How can I assist you today?"

js_state_json = json.dumps(current_state)
js_speak_json = json.dumps(speak_text)

js_code = """
<script>
(function() {
    try {
        const pdoc = window.parent.document;
        const dot = pdoc.getElementById('micDot');
        const statusLabel = pdoc.getElementById('statusLabel');
        const hologramStage = pdoc.getElementById('hologramStage');
        const actionPill = pdoc.getElementById('actionPill');
        const micSelect = pdoc.getElementById('micDeviceSelect');
        const micHeard = pdoc.getElementById('micHeard');
        const recogStatus = pdoc.getElementById('recogStatus');

        const currentKioskState = %CURRENT_STATE%;
        const textToSay = %SPEAK_TEXT%;

        let isSpeaking = false;
        let isTriggered = false;
        let selectedDeviceId = pdoc.defaultView.localStorage.getItem('pxt_mic_device') || '';

        // Sandbox-safe navigation via parent-DOM link click
        function sendPayload(val) {
            if (isTriggered) return;
            isTriggered = true;
            let link = pdoc.getElementById('pxt-nav-link');
            if (!link) {
                link = pdoc.createElement('a');
                link.id = 'pxt-nav-link';
                link.style.display = 'none';
                pdoc.body.appendChild(link);
            }
            const u = new URL(window.parent.location.href);
            u.searchParams.set('voice_payload', val);
            link.href = u.href;
            link.click();
        }

        if (actionPill) {
            actionPill.onclick = function() {
                if (currentKioskState === 'idle') sendPayload('WAKE');
                else startAudioEngine();
            };
        }

        function updateUI(listening, customText) {
            if (!dot || !statusLabel || !hologramStage) return;
            if (listening) {
                dot.className = 'dot listening';
                statusLabel.className = 'status-txt listening';
                statusLabel.innerText = 'LISTENING';
                hologramStage.classList.add('listening');
                if (actionPill) {
                    actionPill.classList.add('listening');
                    if (customText) actionPill.innerText = customText;
                }
            } else {
                dot.className = 'dot';
                statusLabel.className = 'status-txt';
                statusLabel.innerText = 'STANDBY';
                hologramStage.classList.remove('listening');
                if (actionPill) {
                    actionPill.classList.remove('listening');
                    if (currentKioskState === 'idle') actionPill.innerText = 'Say "Hi PXT" or Click here';
                }
            }
        }

        // Populate mic list once permission is granted
        function populateMicList() {
            if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
            navigator.mediaDevices.enumerateDevices().then(function(devs) {
                if (!micSelect) return;
                const mics = devs.filter(function(d){return d.kind==='audioinput';});
                let html = '';
                mics.forEach(function(m){
                    const label = m.label || ('Mic ' + m.deviceId.substring(0,6));
                    const sel = (m.deviceId === selectedDeviceId) ? ' selected' : '';
                    html += '<option value="' + m.deviceId + '"' + sel + '>' + label + '</option>';
                });
                micSelect.innerHTML = html || '<option value="">No mic</option>';
                if (!selectedDeviceId && mics.length > 0) {
                    selectedDeviceId = mics[0].deviceId;
                    pdoc.defaultView.localStorage.setItem('pxt_mic_device', selectedDeviceId);
                }
            });
        }
        if (micSelect) {
            micSelect.onchange = function() {
                selectedDeviceId = micSelect.value;
                pdoc.defaultView.localStorage.setItem('pxt_mic_device', selectedDeviceId);
                window.parent.location.reload();
            };
        }

        // ---- Hardware Audio Stream Meter (ORIGINAL WORKING) ----
        function startAudioEnergyMeter() {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
            // Force the user-picked mic via deviceId (Chrome ignores its own setting here).
            // This also "primes" Chrome's default so SpeechRecognition uses the same mic.
            const audioConstraint = selectedDeviceId
                ? { deviceId: { exact: selectedDeviceId }, echoCancellation: true, noiseSuppression: true, autoGainControl: true }
                : true;
            navigator.mediaDevices.getUserMedia({ audio: audioConstraint, video: false })
                .then(stream => {
                    updateUI(true, 'Say "Hi PXT" or Click here');
                    populateMicList();
                    // DEBUG: log which mic Chrome actually chose (should match Windows default)
                    try {
                        const t = stream.getAudioTracks()[0];
                        console.log('=== ACTUAL MIC IN USE: ' + t.label + ' ===');
                        if (micHeard) micHeard.innerText = 'USING: ' + t.label + '  (speak now)';
                    } catch(e) {}
                    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    const source = audioCtx.createMediaStreamSource(stream);
                    const analyser = audioCtx.createAnalyser();
                    analyser.fftSize = 256;
                    source.connect(analyser);

                    const dataArray = new Uint8Array(analyser.frequencyBinCount);

                    function checkAudio() {
                        if (isSpeaking || isTriggered) {
                            requestAnimationFrame(checkAudio);
                            return;
                        }
                        analyser.getByteFrequencyData(dataArray);
                        let sum = 0, peak = 0;
                        for (let i = 0; i < dataArray.length; i++) { sum += dataArray[i]; if (dataArray[i] > peak) peak = dataArray[i]; }
                        const average = sum / dataArray.length;

                        // Live mic-level indicator so user can SEE if audio is flowing
                        if (micHeard && !window._pxtLastHeardText) {
                            const bars = Math.min(15, Math.floor(peak / 8));
                            const bar = '#'.repeat(bars) + '-'.repeat(15 - bars);
                            const t = stream.getAudioTracks()[0];
                            const label = (t && t.label) ? t.label.substring(0, 30) : '?';
                            micHeard.innerText = 'MIC(' + label + '): [' + bar + ']';
                            micHeard.style.color = peak > 20 ? '#34d399' : '#7dd3fc';
                        }

                        if (average > 25) {
                            if (currentKioskState === 'idle') {
                                if (actionPill) actionPill.innerText = "Voice Detected... Activating!";
                                setTimeout(() => sendPayload('WAKE'), 300);
                                return;
                            }
                        }
                        requestAnimationFrame(checkAudio);
                    }
                    checkAudio();
                })
                .catch(err => {
                    console.log('Microphone access denied:', err);
                    if (statusLabel) statusLabel.innerText = 'MIC BLOCKED';
                    if (actionPill) actionPill.innerText = 'Allow Microphone in Browser';
                });
        }

        // ---- Speech Recognition (ORIGINAL WORKING) ----
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        let recognition = null;

        if (SpeechRecognition) {
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            recognition.onresult = function(event) {
                if (isSpeaking || isTriggered) return;

                let liveText = '';
                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    liveText += event.results[i][0].transcript;
                }
                liveText = liveText.trim();
                const lower = liveText.toLowerCase();

                if (liveText.length > 0) {
                    window._pxtLastHeardText = true;  // stop overwriting HEARD with the meter
                    if (actionPill) actionPill.innerText = 'Heard: "' + liveText + '"';
                    if (micHeard) { micHeard.innerText = 'HEARD: ' + liveText; micHeard.style.color = '#34d399'; }
                    if (recogStatus) { recogStatus.innerText = 'RECOGNITION: OK — words received ✔'; recogStatus.style.color = '#34d399'; }
                }

                if (currentKioskState === 'idle') {
                    const clean = lower.replace(/[^a-z0-9]/g, '');
                    if (clean.includes('pxt') || clean.includes('hi') || clean.includes('hello') || clean.includes('wake')) {
                        sendPayload('WAKE');
                    }
                } else if (liveText.length > 1) {
                    sendPayload(liveText);
                }
            };

            recognition.onstart = function() {
                if (recogStatus) { recogStatus.innerText = 'RECOGNITION: listening…'; recogStatus.style.color = '#7dd3fc'; }
            };

            recognition.onaudiostart = function() {
                if (recogStatus) { recogStatus.innerText = 'RECOGNITION: audio detected — analyzing…'; recogStatus.style.color = '#38bdf8'; }
            };

            recognition.onspeechstart = function() {
                if (recogStatus) { recogStatus.innerText = 'RECOGNITION: speech detected! processing…'; recogStatus.style.color = '#a78bfa'; }
            };

            recognition.onspeechend = function() {
                if (recogStatus && !window._pxtLastHeardText) { recogStatus.innerText = 'RECOGNITION: speech ended, waiting on transcript…'; recogStatus.style.color = '#a78bfa'; }
            };

            // Counts consecutive no-speech errors so we can tell you when it's
            // not a fluke — i.e. the recognizer genuinely never hears you.
            window._pxtNoSpeechStreak = window._pxtNoSpeechStreak || 0;

            recognition.onerror = function(e) {
                console.log('Recognition status:', e.error);
                if (!recogStatus) return;
                if (e.error === 'no-speech') {
                    window._pxtNoSpeechStreak++;
                    const hint = window._pxtNoSpeechStreak >= 3
                        ? ' — mic bar working but this stays empty? Recognition is on a DIFFERENT device than the meter. Fix in Windows Sound settings: set the headset as BOTH Default Device AND Default Communication Device.'
                        : '';
                    recogStatus.innerText = 'RECOGNITION: no-speech (' + window._pxtNoSpeechStreak + 'x)' + hint;
                    recogStatus.style.color = '#f59e0b';
                } else if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
                    recogStatus.innerText = 'RECOGNITION: blocked — mic permission denied for speech (' + e.error + ')';
                    recogStatus.style.color = '#f87171';
                } else if (e.error === 'network') {
                    recogStatus.innerText = 'RECOGNITION: network error — this needs internet access to Google\\'s speech service';
                    recogStatus.style.color = '#f87171';
                } else if (e.error === 'audio-capture') {
                    recogStatus.innerText = 'RECOGNITION: audio-capture — no mic hardware found by the recognizer';
                    recogStatus.style.color = '#f87171';
                } else {
                    recogStatus.innerText = 'RECOGNITION: error — ' + e.error;
                    recogStatus.style.color = '#f87171';
                }
            };

            recognition.onend = function() {
                if (!isSpeaking && !isTriggered && !window._pxtRestarting) {
                    window._pxtRestarting = true;
                    // Delay avoids slamming Chrome with instant restarts, which
                    // can cause an infinite start/end loop and repeated mic
                    // permission prompts instead of ever actually listening.
                    setTimeout(function() {
                        window._pxtRestarting = false;
                        if (!isSpeaking && !isTriggered) {
                            try { recognition.start(); } catch(e) {}
                        }
                    }, 400);
                }
            };
        } else {
            if (recogStatus) { recogStatus.innerText = 'RECOGNITION: not supported in this browser'; recogStatus.style.color = '#f87171'; }
        }

        function startAudioEngine() {
            startAudioEnergyMeter();
            if (recognition) {
                try { recognition.start(); } catch(e) {}
            }
        }

        // TTS then engine
        if (textToSay && 'speechSynthesis' in window) {
            isSpeaking = true;
            window.speechSynthesis.cancel();
            const ut = new SpeechSynthesisUtterance(textToSay);
            ut.rate = 0.95;
            ut.onend = function() { isSpeaking = false; startAudioEngine(); };
            ut.onerror = function() { isSpeaking = false; startAudioEngine(); };
            window.speechSynthesis.speak(ut);
        } else {
            startAudioEngine();
        }

    } catch(err) {
        console.log('Audio Bridge error:', err);
    }
})();
</script>
""".replace("%CURRENT_STATE%", js_state_json).replace("%SPEAK_TEXT%", js_speak_json)

components.html(js_code, height=1)

# Bottom deck
st.markdown('<div class="kiosk-ui-container">', unsafe_allow_html=True)

if current_state == "asked_badge":
    badge_in = st.text_input("badge_in", placeholder="Enter Badge ID (e.g. EMP011) or speak", label_visibility="collapsed")
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
            st.error("Badge ID not recognized. Please try again.")

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
    q_box = st.text_input("ask_q", placeholder="Ask a question or speak", label_visibility="collapsed")
    active_q = st.session_state.get("last_heard") or q_box
    if active_q and active_q != "WAKE":
        st.session_state["last_interaction"] = time.time()
        ans = answer_employee_question(emp, active_q)
        st.session_state["last_heard"] = ""
        st.success(ans)

st.markdown('</div>', unsafe_allow_html=True)
