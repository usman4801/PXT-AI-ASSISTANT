"""
PXT Hub — AI Voice Kiosk
=========================
A full-screen, browser-mic-based voice kiosk built with Streamlit.

IMPORTANT DEPLOYMENT NOTE:
Browser speech recognition (Web Speech API) only works over HTTPS or on
localhost. Streamlit Community Cloud serves over HTTPS by default, so
deployment there works out of the box. If you run this on a local
network kiosk laptop without HTTPS, use `localhost` (not a LAN IP) or
set up a local TLS certificate, otherwise Chrome will silently block
the microphone.

Supported/tested browser: Google Chrome or Microsoft Edge (both use the
webkitSpeechRecognition engine). Firefox/Safari do not support the
wake-word style continuous recognition used here.
"""

import json
import os

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------
CSV_PATH = "staff_data.csv"
ADMIN_PASSWORD = "pxt123"
REQUIRED_COLUMNS = ["EmployeeID", "Name", "Status", "RemainingLeaves", "NextOffDay"]

st.set_page_config(
    page_title="PXT Hub",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --------------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------------
def load_staff_data() -> pd.DataFrame:
    if os.path.exists(CSV_PATH):
        try:
            df = pd.read_csv(CSV_PATH, dtype=str).fillna("")
            missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
            if missing:
                st.error(
                    f"staff_data.csv is missing required column(s): {', '.join(missing)}. "
                    f"Required columns: {', '.join(REQUIRED_COLUMNS)}"
                )
                return pd.DataFrame(columns=REQUIRED_COLUMNS)
            return df
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not read staff_data.csv: {exc}")
            return pd.DataFrame(columns=REQUIRED_COLUMNS)
    return pd.DataFrame(columns=REQUIRED_COLUMNS)


def df_to_json_records(df: pd.DataFrame) -> str:
    records = df.to_dict(orient="records")
    # Keys used by the JS layer are lowercase / normalized for matching.
    cleaned = [
        {
            "id": str(r.get("EmployeeID", "")).strip(),
            "name": str(r.get("Name", "")).strip(),
            "status": str(r.get("Status", "")).strip(),
            "leaves": str(r.get("RemainingLeaves", "")).strip(),
            "nextoff": str(r.get("NextOffDay", "")).strip(),
        }
        for r in records
    ]
    return json.dumps(cleaned)


# --------------------------------------------------------------------------
# GLOBAL CSS — strip Streamlit chrome, make the component fill the screen
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        div.block-container {padding: 0 !important; margin: 0 !important; max-width: 100% !important;}
        html, body, [data-testid="stAppViewContainer"] {
            background: #05070c;
            overflow: hidden;
        }
        [data-testid="stSidebar"] {
            background: #0a0d14;
        }
        /* Make the kiosk iframe cover the full viewport */
        iframe[title="st.iframe"], [data-testid="stIFrame"] iframe, iframe {
            position: fixed !important;
            top: 0; left: 0;
            width: 100vw !important;
            height: 100vh !important;
            border: none !important;
            z-index: 1;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# ADMIN PANEL (discreet — collapsed sidebar, password protected)
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🔒 PXT Admin")
    pwd = st.text_input("Admin password", type="password", label_visibility="collapsed",
                         placeholder="Admin password")
    if pwd == ADMIN_PASSWORD:
        st.success("Access granted")
        st.caption("Upload a replacement staff database (.csv)")
        uploaded = st.file_uploader("Upload staff_data.csv", type=["csv"], label_visibility="collapsed")
        if uploaded is not None:
            try:
                new_df = pd.read_csv(uploaded, dtype=str).fillna("")
                missing = [c for c in REQUIRED_COLUMNS if c not in new_df.columns]
                if missing:
                    st.error(f"Missing column(s): {', '.join(missing)}")
                else:
                    new_df.to_csv(CSV_PATH, index=False)
                    st.success("Database updated. Reloading kiosk...")
                    st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Failed to process file: {exc}")

        st.divider()
        st.caption("Current records")
        st.dataframe(load_staff_data(), use_container_width=True, height=300)
    elif pwd:
        st.error("Incorrect password")

# --------------------------------------------------------------------------
# LOAD DATA
# --------------------------------------------------------------------------
staff_df = load_staff_data()
staff_json = df_to_json_records(staff_df)

# --------------------------------------------------------------------------
# KIOSK HTML/JS COMPONENT
# --------------------------------------------------------------------------
KIOSK_HTML = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    * { box-sizing: border-box; }
    html, body {
        margin: 0; padding: 0; width: 100%; height: 100%;
        background: #05070c;
        font-family: 'Segoe UI', Arial, sans-serif;
        overflow: hidden;
    }

    .kiosk-wrap {
        position: relative;
        width: 100vw; height: 100vh;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }

    /* Animated dark tech background (works with zero external assets).
       If VIDEO_SRC is provided, a looping <video> is layered underneath instead. */
    .bg-video {
        position: absolute; inset: 0;
        width: 100%; height: 100%;
        object-fit: cover;
        z-index: 0;
        opacity: 0.85;
    }
    .bg-fallback {
        position: absolute; inset: 0;
        z-index: 0;
        background:
            radial-gradient(circle at 20% 30%, rgba(0,180,255,0.15), transparent 45%),
            radial-gradient(circle at 80% 70%, rgba(0,255,200,0.12), transparent 45%),
            linear-gradient(120deg, #05070c, #0a0f1a 40%, #05070c 100%);
        background-size: 200% 200%;
        animation: bgshift 18s ease-in-out infinite;
    }
    @keyframes bgshift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    .grid-overlay {
        position: absolute; inset: 0; z-index: 0;
        background-image:
            linear-gradient(rgba(0,220,255,0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,220,255,0.05) 1px, transparent 1px);
        background-size: 42px 42px;
        mask-image: radial-gradient(circle at 50% 40%, black 10%, transparent 75%);
    }
    .scrim {
        position: absolute; inset: 0; z-index: 1;
        background: radial-gradient(circle at 50% 45%, rgba(5,7,12,0.15), rgba(5,7,12,0.85) 75%);
    }

    .brand {
        position: relative; z-index: 2;
        color: #e8f6ff;
        letter-spacing: 6px;
        font-size: 18px;
        font-weight: 600;
        opacity: 0.75;
        margin-bottom: 26px;
        text-transform: uppercase;
    }

    .spacer { height: 6vh; }

    .result-card {
        position: relative; z-index: 2;
        width: min(560px, 88vw);
        background: rgba(15, 22, 34, 0.72);
        border: 1px solid rgba(90, 210, 255, 0.25);
        border-radius: 22px;
        padding: 28px 34px;
        backdrop-filter: blur(14px);
        color: #eaf6ff;
        text-align: center;
        display: none;
        box-shadow: 0 0 40px rgba(0,150,255,0.15);
    }
    .result-card.show { display: block; animation: fadein .35s ease; }
    @keyframes fadein { from { opacity: 0; transform: translateY(8px);} to { opacity: 1; transform: translateY(0);} }
    .result-name { font-size: 26px; font-weight: 700; margin-bottom: 4px; }
    .result-id { font-size: 13px; letter-spacing: 2px; color: #7fd8ff; opacity: 0.8; margin-bottom: 18px; text-transform: uppercase; }
    .result-grid { display: flex; justify-content: space-around; gap: 12px; flex-wrap: wrap; }
    .result-item { min-width: 120px; }
    .result-item .label { font-size: 11px; letter-spacing: 1.5px; color: #8fb8cf; text-transform: uppercase; margin-bottom: 6px; }
    .result-item .value { font-size: 19px; font-weight: 600; }
    .status-present { color: #4dffb0; }
    .status-absent  { color: #ff6767; }
    .status-other   { color: #ffd166; }

    .pill {
        position: fixed;
        bottom: 46px; left: 50%;
        transform: translateX(-50%);
        z-index: 3;
        display: flex; flex-direction: column; align-items: center;
        gap: 6px;
        padding: 14px 34px;
        border-radius: 999px;
        background: rgba(10, 16, 26, 0.65);
        border: 1px solid rgba(80, 200, 255, 0.35);
        backdrop-filter: blur(10px);
        box-shadow: 0 0 22px rgba(0, 190, 255, 0.35), inset 0 0 12px rgba(0,190,255,0.08);
        animation: glow 2.4s ease-in-out infinite;
        text-align: center;
        max-width: 90vw;
    }
    @keyframes glow {
        0%, 100% { box-shadow: 0 0 18px rgba(0,190,255,0.28), inset 0 0 10px rgba(0,190,255,0.06); }
        50%      { box-shadow: 0 0 34px rgba(0,190,255,0.55), inset 0 0 16px rgba(0,190,255,0.12); }
    }
    .pill .line1 { color: #dff5ff; font-size: 15px; font-weight: 600; letter-spacing: 0.4px; }
    .pill .line2 { color: #7fd0ef; font-size: 12.5px; letter-spacing: 0.3px; opacity: 0.85; }

    .mic-dot {
        position: fixed; top: 22px; right: 26px; z-index: 3;
        width: 10px; height: 10px; border-radius: 50%;
        background: #ff5b5b;
        box-shadow: 0 0 10px rgba(255,80,80,0.8);
    }
    .mic-dot.on { background: #46ffb0; box-shadow: 0 0 10px rgba(70,255,176,0.9); }

    .debug-caption {
        position: fixed;
        top: 22px; left: 50%; transform: translateX(-50%);
        z-index: 3;
        color: #7fd0ef;
        font-size: 13px;
        letter-spacing: 0.3px;
        background: rgba(10,16,26,0.55);
        padding: 6px 16px;
        border-radius: 999px;
        border: 1px solid rgba(80,200,255,0.2);
        max-width: 80vw;
        text-align: center;
        opacity: 0.85;
        min-height: 14px;
    }
</style>
</head>
<body>
<div class="kiosk-wrap">
    <video class="bg-video" id="bgVideo" autoplay muted loop playsinline style="display:none;"></video>
    <div class="bg-fallback"></div>
    <div class="grid-overlay"></div>
    <div class="scrim"></div>

    <div class="mic-dot" id="micDot" title="Microphone status"></div>
    <div class="debug-caption" id="debugCaption">&nbsp;</div>

    <div class="brand">PXT&nbsp;HUB</div>

    <div class="spacer"></div>

    <div class="result-card" id="resultCard">
        <div class="result-name" id="rName">—</div>
        <div class="result-id" id="rId">—</div>
        <div class="result-grid">
            <div class="result-item">
                <div class="label">Status</div>
                <div class="value" id="rStatus">—</div>
            </div>
            <div class="result-item">
                <div class="label">Leaves Left</div>
                <div class="value" id="rLeaves">—</div>
            </div>
            <div class="result-item">
                <div class="label">Next Off Day</div>
                <div class="value" id="rNext">—</div>
            </div>
        </div>
    </div>

    <div class="pill">
        <div class="line1" id="pillLine1">I am your PXT AI Assistant</div>
        <div class="line2" id="pillLine2">Say "Hi PXT" to start...</div>
    </div>
</div>

<script>
(function () {
    const STAFF = __STAFF_DATA_JSON__;
    const VIDEO_SRC = "__VIDEO_SRC__"; // optional: set a URL/path to a looping mp4 for a richer background

    const micDot = document.getElementById('micDot');
    const pillLine1 = document.getElementById('pillLine1');
    const pillLine2 = document.getElementById('pillLine2');
    const resultCard = document.getElementById('resultCard');
    const rName = document.getElementById('rName');
    const rId = document.getElementById('rId');
    const rStatus = document.getElementById('rStatus');
    const rLeaves = document.getElementById('rLeaves');
    const rNext = document.getElementById('rNext');
    const bgVideo = document.getElementById('bgVideo');
    const debugCaption = document.getElementById('debugCaption');

    // The video plays through the kiosk speakers and bleeds back into the mic,
    // which corrupts wake-word / name recognition. Keeping volume moderate (not
    // full blast) is the single biggest fix for that — it's an acoustic problem,
    // not something code alone can fully cancel. Adjust this if needed.
    const IDLE_VIDEO_VOLUME = 0.35;      // while waiting for "Hi PXT"
    const LISTENING_VIDEO_VOLUME = 0.12; // ducked further while capturing name/login
    bgVideo.volume = IDLE_VIDEO_VOLUME;

    if (VIDEO_SRC && VIDEO_SRC.trim() !== "") {
        bgVideo.src = VIDEO_SRC;
        bgVideo.style.display = "block";
        const fallback = document.querySelector('.bg-fallback');
        bgVideo.addEventListener('playing', function () {
            if (fallback) fallback.style.display = "none";
        });
    }

    // Exact-phrase matching was too brittle — the recognizer reliably hears
    // "hi"/"high"/"hey" and the "px" sound, but the trailing consonant of "PXT"
    // is unreliable (often heard as "pxd", "pxt", "pect", etc). So we match
    // loosely: a greeting word, plus something that sounds like "px".
    function isWakeWord(t) {
        const hasGreeting = /\b(hi|high|hey|hai|hey)\b/.test(t);
        const hasPX = /\bp\s?x\s?[a-z]{0,3}\b/.test(t) || t.replace(/\s+/g, "").includes("px");
        return hasGreeting && hasPX;
    }

    let state = "idle"; // idle | awaiting_id | result
    let recognition = null;
    let shouldRun = true;
    let resetTimer = null;
    let lastResultAt = Date.now();
    let watchdog = null;

    function setPill(line1, line2) {
        pillLine1.textContent = line1;
        pillLine2.textContent = line2;
    }

    function speak(text, onend) {
        try {
            window.speechSynthesis.cancel();
            const utter = new SpeechSynthesisUtterance(text);
            utter.rate = 1.0;
            utter.pitch = 1.0;
            utter.lang = "en-US";
            if (onend) utter.onend = onend;
            window.speechSynthesis.speak(utter);
        } catch (e) { /* speech synthesis unsupported */ }
    }

    function normalize(s) {
        return (s || "").toLowerCase().trim().replace(/[^a-z0-9 ]/g, "").replace(/\s+/g, " ");
    }

    function findStaff(transcript) {
        const t = normalize(transcript);
        const tNoSpace = t.replace(/\s+/g, "");
        if (!t) return null;

        // 1) Try login/employee ID match (e.g. "emp001")
        for (const s of STAFF) {
            const idNorm = normalize(s.id).replace(/\s+/g, "");
            if (idNorm && (tNoSpace.includes(idNorm) || idNorm.includes(tNoSpace))) {
                return s;
            }
        }
        // 2) Try full name match
        for (const s of STAFF) {
            const nameNorm = normalize(s.name);
            if (nameNorm && t.includes(nameNorm)) return s;
        }
        // 3) Try partial / token match (all tokens of the staff name present in transcript)
        for (const s of STAFF) {
            const tokens = normalize(s.name).split(" ").filter(Boolean);
            if (tokens.length && tokens.every(tok => t.includes(tok))) return s;
        }
        return null;
    }

    function statusClass(status) {
        const s = (status || "").toLowerCase();
        if (s.includes("present")) return "status-present";
        if (s.includes("absent")) return "status-absent";
        return "status-other";
    }

    function showResult(staff) {
        state = "result";
        resultCard.classList.add("show");
        rName.textContent = staff.name;
        rId.textContent = staff.id;
        rStatus.textContent = staff.status || "—";
        rStatus.className = "value " + statusClass(staff.status);
        rLeaves.textContent = staff.leaves || "—";
        rNext.textContent = staff.nextoff || "—";

        setPill("Here is your update, " + staff.name.split(" ")[0], "Resetting shortly...");

        const sentence = "Hello " + staff.name + ". Your status is " + staff.status +
            ". You have " + staff.leaves + " leaves remaining. Your next off day is " + staff.nextoff + ".";
        speak(sentence);

        clearTimeout(resetTimer);
        resetTimer = setTimeout(resetToIdle, 8000);
    }

    function resetToIdle() {
        state = "idle";
        bgVideo.volume = IDLE_VIDEO_VOLUME;
        resultCard.classList.remove("show");
        setPill("I am your PXT AI Assistant", "Say \"Hi PXT\" to start...");
    }

    function handleTranscript(transcript) {
        const t = normalize(transcript);
        if (state === "idle") {
            if (isWakeWord(t)) {
                state = "awaiting_id";
                bgVideo.volume = LISTENING_VIDEO_VOLUME;
                setPill("Kindly tell me your login or name", "Listening...");
                speak("Kindly tell me your login or name.");
            }
        } else if (state === "awaiting_id") {
            const staff = findStaff(transcript);
            if (staff) {
                showResult(staff);
            } else {
                setPill("Sorry, I couldn't find that record", "Say \"Hi PXT\" to try again");
                speak("Sorry, I could not find your record. Please try again.");
                clearTimeout(resetTimer);
                resetTimer = setTimeout(resetToIdle, 2500);
            }
        }
        // while in "result" state, incoming speech is ignored until reset.
    }

    function initRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            setPill("Voice not supported", "Please use Chrome or Edge browser");
            return;
        }
        startSpeechRecognition(SpeechRecognition);
    }

    function startSpeechRecognition(SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = "en-US";
        recognition.maxAlternatives = 1;

        recognition.onstart = function () {
            micDot.classList.add("on");
            if (state === "idle") debugCaption.textContent = "Listening... say \"Hi PXT\"";
        };
        recognition.onend = function () {
            micDot.classList.remove("on");
            if (shouldRun) {
                setTimeout(function () {
                    try { recognition.start(); } catch (e) { /* already started */ }
                }, 250);
            }
        };
        recognition.onerror = function (e) {
            // no-speech / audio-capture / network errors are recoverable — just let onend restart it.
            micDot.classList.remove("on");
            debugCaption.textContent = "mic error: " + e.error;
        };
        recognition.onresult = function (event) {
            lastResultAt = Date.now();
            let liveText = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
                liveText += event.results[i][0].transcript;
            }
            debugCaption.textContent = "Heard: " + liveText;

            const last = event.results[event.results.length - 1];
            if (last.isFinal) {
                const transcript = last[0].transcript;
                handleTranscript(transcript);
            }
        };

        try { recognition.start(); } catch (e) { /* ignore */ }

        clearInterval(watchdog);
        watchdog = setInterval(function () {
            if (state === "idle" && Date.now() - lastResultAt > 12000) {
                debugCaption.textContent = "No audio detected — restarting mic...";
                try { recognition.stop(); } catch (e) {}
                try { recognition.abort(); } catch (e) {}
                lastResultAt = Date.now();
            }
        }, 4000);
    }

    // Kiosk mode: everything starts automatically on load — video plays with sound
    // and the mic begins listening right away. No tap/click required.
    // NOTE: for the video to play WITH SOUND automatically, Chrome must be launched
    // with the flag --autoplay-policy=no-user-gesture-required (see deployment notes).
    window.addEventListener("load", function () {
        bgVideo.muted = false;
        bgVideo.play().catch(function () {
            // Autoplay-with-sound was blocked by the browser. Fall back to muted
            // playback so the video still runs, and keep retrying unmute shortly.
            bgVideo.muted = true;
            bgVideo.play().catch(function () {});
            const retryUnmute = setInterval(function () {
                bgVideo.muted = false;
                bgVideo.play().then(function () { clearInterval(retryUnmute); }).catch(function () {});
            }, 3000);
        });
        setTimeout(initRecognition, 300);
        try {
            const warm = new SpeechSynthesisUtterance(' ');
            warm.volume = 0;
            window.speechSynthesis.speak(warm);
        } catch (e) {}
    });

    window.addEventListener("beforeunload", function () {
        shouldRun = false;
        if (recognition) { try { recognition.stop(); } catch (e) {} }
    });
})();
</script>
</body>
</html>
"""

KIOSK_HTML = KIOSK_HTML.replace("__STAFF_DATA_JSON__", staff_json)
VIDEO_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner.mp4"
KIOSK_HTML = KIOSK_HTML.replace("__VIDEO_SRC__", VIDEO_URL)

st.components.v1.html(KIOSK_HTML, height=1000, scrolling=False)
