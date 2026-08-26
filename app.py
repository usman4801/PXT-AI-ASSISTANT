"""
PXT Hub — AI Voice Kiosk
=========================
A full-screen, browser-mic-based voice kiosk built with Streamlit.
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
    cleaned = [
        {
            "id": str(r.get("EmployeeID", "")).strip(),
            "name": str(r.get("Name", "")).strip(),
            "status": str(r.get("Status", "")).strip(),
            "leaves": str(r.get("RemainingLeaves", "")).strip(),
            "nextoff": str(r.get("NextOffDay", "")).strip(),
            "aliases": [
                a.strip() for a in str(r.get("Aliases", "")).split("|") if a.strip()
            ],
        }
        for r in records
    ]
    return json.dumps(cleaned, ensure_ascii=False)


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
# ADMIN PANEL
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

    <div class="brand">PXT&nbspHUB</div>
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
    const VIDEO_SRC = "__VIDEO_SRC__";

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

    const IDLE_VIDEO_VOLUME = 0.35;
    const LISTENING_VIDEO_VOLUME = 0.12;
    bgVideo.volume = IDLE_VIDEO_VOLUME;

    if (VIDEO_SRC && VIDEO_SRC.trim() !== "") {
        bgVideo.src = VIDEO_SRC;
        bgVideo.style.display = "block";
        const fallback = document.querySelector('.bg-fallback');
        bgVideo.addEventListener('playing', function () {
            if (fallback) fallback.style.display = "none";
        });
    }

    const WAKE_LANG = "en-US";

    // Language configurations for reply templates
    const LANGUAGES = {
        "en": { code: "en-US", reply: (n,s,l,d) => `Hello ${n}. Your status is ${s}. You have ${l} leaves remaining. Your next off day is ${d}.`, sorry: "Sorry, I could not find your record. Please try again." },
        "ur": { code: "ur-PK", reply: (n,s,l,d) => `السلام علیکم ${n}۔ آپ کی حاضری کی صورتحال ${s} ہے۔ آپ کی ${l} چھٹیاں باقی ہیں۔ آپ کی اگلی چھٹی کا دن ${d} ہے۔`, sorry: "معذرت، آپ کا ریکارڈ نہیں ملا۔ دوبارہ کوشش کریں۔" },
        "hi": { code: "hi-IN", reply: (n,s,l,d) => `नमस्ते ${n}। आपकी स्थिति ${s} है। आपकी ${l} छुट्टियाँ शेष हैं। आपका अगला अवकाश दिन ${d} है।`, sorry: "क्षमा करें, आपका रिकॉर्ड नहीं मिला। कृपया पुनः प्रयास करें।" },
        "ta": { code: "ta-IN", reply: (n,s,l,d) => `வணக்கம் ${n}. உங்கள் நிலை ${s}. உங்களுக்கு ${l} விடுப்பு மீதம் உள்ளது. உங்கள் அடுத்த ஓய்வு நாள் ${d}.`, sorry: "மன்னிக்கவும், உங்கள் பதிவு கிடைக்கவில்லை. மீண்டும் முயற்சிக்கவும்." },
        "ml": { code: "ml-IN", reply: (n,s,l,d) => `ഹലോ ${n}. നിങ്ങളുടെ സ്ഥിതി ${s} ആണ്. നിങ്ങൾക്ക് ${l} അവധി ദിനങ്ങൾ ബാക്കിയുണ്ട്. നിങ്ങളുടെ അടുത്ത അവധി ദിവസം ${d} ആണ്.`, sorry: "ക്ഷമിക്കണം, നിങ്ങളുടെ റെക്കോർഡ് കണ്ടെത്താനായില്ല. വീണ്ടും ശ്രമിക്കുക." },
        "am": { code: "am-ET", reply: (n,s,l,d) => `ሰላም ${n}። ሁኔታዎ ${s} ነው። ${l} ቀሪ የእረፍት ቀናት አሉዎት። ቀጣዩ የእረፍት ቀንዎ ${d} ነው።`, sorry: "ይቅርታ፣ መዝገብዎ አልተገኘም። እባክዎ ደግመው ይሞክሩ።" },
        "yo": { code: "yo-NG", reply: (n,s,l,d) => `Bawo ni ${n}. Ipo rẹ ni ${s}. O ni ọjọ isinmi ${l} to ku. Ọjọ isinmi rẹ to nbọ ni ${d}.`, sorry: "Ma binu, mi ò rí àkọsílẹ̀ rẹ. Jọwọ tún gbìyànjú." },
        "ha": { code: "ha-NG", reply: (n,s,l,d) => `Sannu ${n}. Matsayin ku shine ${s}. Kuna da hutu ${l} da suka rage. Ranar hutunku ta gaba shine ${d}.`, sorry: "Yi hakuri, ban sami bayanan ku ba. Don Allah a sake gwadawa." },
        "ig": { code: "ig-NG", reply: (n,s,l,d) => `Ndewo ${n}. Ọnọdụ gị bụ ${s}. I nwere ezumike ${l} fọdụrụ. Ụbọchị izu ike gị na-abịa bụ ${d}.`, sorry: "Ndo, achọtaghị ndekọ gị. Biko nwaa ọzọ." },
        "lg": { code: "lg-UG", reply: (n,s,l,d) => `Ki kati ${n}. Embeera yo eri ${s}. Olina ${l} ez'okuwummula ezisigadde. Olunaku lwo olw'okuwummula oluddako lwe ${d}.`, sorry: "Nsonyiwa, sisobodde kufuna ndagiriro yo. Ddamu ogezeeko." }
    };

    let state = "idle"; // idle | awaiting_id | result
    let activeRecognition = null;
    let resetTimer = null;

    function setPill(line1, line2) {
        pillLine1.textContent = line1;
        pillLine2.textContent = line2;
    }

    function speak(text, lang, onend) {
        try {
            window.speechSynthesis.cancel();
            const utter = new SpeechSynthesisUtterance(text);
            utter.rate = 1.0;
            utter.pitch = 1.0;
            utter.lang = lang || "en-US";
            if (onend) utter.onend = onend;
            window.speechSynthesis.speak(utter);
        } catch (e) {}
    }

    function normalize(s) {
        return (s || "").toLowerCase().trim()
            .replace(/[^\p{L}\p{N}\s]/gu, "")
            .replace(/\s+/g, " ");
    }

    function findStaff(transcript) {
        const t = normalize(transcript);
        const tNoSpace = t.replace(/\s+/g, "");
        if (!t) return null;

        for (const s of STAFF) {
            const idNorm = normalize(s.id).replace(/\s+/g, "");
            if (idNorm && (tNoSpace.includes(idNorm) || idNorm.includes(tNoSpace))) return s;
        }
        for (const s of STAFF) {
            const nameNorm = normalize(s.name);
            if (nameNorm && t.includes(nameNorm)) return s;
        }
        for (const s of STAFF) {
            for (const alias of (s.aliases || [])) {
                const aliasNorm = normalize(alias);
                if (aliasNorm && t.includes(aliasNorm)) return s;
            }
        }
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

    // Smart detection for Roman Urdu, Hindi, or native scripts to reply in correct language
    function detectLanguageFromTranscript(transcript) {
        const t = transcript || "";
        const lower = t.toLowerCase();

        // Native script checks
        if (/[\u0600-\u06FF]/.test(t)) return LANGUAGES["ur"];
        if (/[\u0900-\u097F]/.test(t)) return LANGUAGES["hi"];
        if (/[\u0B80-\u0BFF]/.test(t)) return LANGUAGES["ta"];
        if (/[\u0D00-\u0D7F]/.test(t)) return LANGUAGES["ml"];
        if (/[\u1200-\u137F]/.test(t)) return LANGUAGES["am"];

        // Roman Urdu / Hindi conversational keywords
        const urduKeywords = ["mera", "naam", "hai", "mujhe", "meri", "chhutti", "chutti", "kaun", "kya", "aap"];
        const words = lower.split(/\s+/);
        if (urduKeywords.some(kw => words.includes(kw)) || lower.includes("mera naam")) {
            return LANGUAGES["ur"];
        }

        // African & other language triggers
        if (lower.includes("luganda") || lower.includes("uganda")) return LANGUAGES["lg"];
        if (lower.includes("yoruba")) return LANGUAGES["yo"];
        if (lower.includes("hausa")) return LANGUAGES["ha"];
        if (lower.includes("igbo")) return LANGUAGES["ig"];

        return LANGUAGES["en"];
    }

    function showResult(staff, langCfg) {
        state = "result";
        resultCard.classList.add("show");
        rName.textContent = staff.name;
        rId.textContent = staff.id;
        rStatus.textContent = staff.status || "—";
        rStatus.className = "value " + statusClass(staff.status);
        rLeaves.textContent = staff.leaves || "—";
        rNext.textContent = staff.nextoff || "—";

        setPill("Here is your update, " + staff.name.split(" ")[0], "Resetting shortly...");

        const sentence = langCfg.reply(staff.name, staff.status, staff.leaves, staff.nextoff);
        speak(sentence, langCfg.code);

        clearTimeout(resetTimer);
        resetTimer = setTimeout(resetToIdle, 8000);
    }

    function resetToIdle() {
        state = "idle";
        bgVideo.volume = IDLE_VIDEO_VOLUME;
        resultCard.classList.remove("show");
        setPill("I am your PXT AI Assistant", "Say \"Hi PXT\" to start...");
        stopActiveRecognition();
        try { wakeRecognition.start(); } catch (e) {}
    }

    let wakeRecognition = null;
    let shouldRun = true;
    let lastResultAt = Date.now();
    let watchdog = null;

    function isWakeWord(t) {
        const hasGreeting = /\b(hi|high|hey|hai)\b/.test(t);
        const hasPX = /\bp\s?x\s?[a-z]{0,3}\b/.test(t) || t.replace(/\s+/g, "").includes("px");
        return hasGreeting && hasPX;
    }

    function initWakeRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            setPill("Voice not supported", "Please use Chrome or Edge browser");
            return;
        }
        wakeRecognition = new SpeechRecognition();
        wakeRecognition.continuous = true;
        wakeRecognition.interimResults = true;
        wakeRecognition.lang = WAKE_LANG;
        wakeRecognition.maxAlternatives = 1;

        wakeRecognition.onstart = function () {
            micDot.classList.add("on");
            if (state === "idle") debugCaption.textContent = "Listening... say \"Hi PXT\"";
        };
        wakeRecognition.onend = function () {
            micDot.classList.remove("on");
            if (shouldRun && state === "idle") {
                setTimeout(function () {
                    try { wakeRecognition.start(); } catch (e) {}
                }, 250);
            }
        };
        wakeRecognition.onerror = function (e) {
            micDot.classList.remove("on");
            if (state === "idle") debugCaption.textContent = "mic error: " + e.error;
        };
        wakeRecognition.onresult = function (event) {
            if (state !== "idle") return;
            lastResultAt = Date.now();
            let liveText = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
                liveText += event.results[i][0].transcript;
            }
            debugCaption.textContent = "Heard: " + liveText;

            const last = event.results[event.results.length - 1];
            if (last.isFinal && isWakeWord(normalize(last[0].transcript))) {
                try { wakeRecognition.stop(); } catch (e) {}
                startNameCaptureDirect();
            }
        };

        try { wakeRecognition.start(); } catch (e) {}

        clearInterval(watchdog);
        watchdog = setInterval(function () {
            if (state === "idle" && Date.now() - lastResultAt > 12000) {
                debugCaption.textContent = "No audio detected — restarting mic...";
                try { wakeRecognition.stop(); } catch (e) {}
                try { wakeRecognition.abort(); } catch (e) {}
                lastResultAt = Date.now();
            }
        }, 4000);
    }

    function stopActiveRecognition() {
        if (activeRecognition) { try { activeRecognition.stop(); } catch (e) {} try { activeRecognition.abort(); } catch (e) {} }
    }

    // Direct Name Capture — NO language selection prompt at all!
    const NAME_PROMPT_TEXT = "Tell me your login or name.";

    function startNameCaptureDirect() {
        state = "awaiting_id";
        bgVideo.volume = LISTENING_VIDEO_VOLUME;
        setPill("Tell me your login or name", "Listening...");

        let started = false;
        function begin() {
            if (started || state !== "awaiting_id") return;
            started = true;
            listenForNameDirect();
        }
        speak(NAME_PROMPT_TEXT, "en-US", begin);
        setTimeout(begin, 3500);
    }

    function listenForNameDirect() {
        if (state !== "awaiting_id") return;
        debugCaption.textContent = "Listening for name or login...";

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        activeRecognition = new SpeechRecognition();
        activeRecognition.continuous = false;
        activeRecognition.interimResults = true;
        activeRecognition.lang = "en-US";
        activeRecognition.maxAlternatives = 1;

        let gotFinal = false;

        activeRecognition.onresult = function (event) {
            let liveText = "";
            for (let i = 0; i < event.results.length; i++) liveText += event.results[i][0].transcript;
            debugCaption.textContent = "Heard: " + liveText;

            const last = event.results[event.results.length - 1];
            if (last.isFinal) {
                gotFinal = true;
                const transcriptText = last[0].transcript;
                const staff = findStaff(transcriptText);
                const detectedLang = detectLanguageFromTranscript(transcriptText);

                if (staff) {
                    showResult(staff, detectedLang);
                } else {
                    setPill("Sorry, I couldn't find that record", "Say \"Hi PXT\" to try again");
                    speak(detectedLang.sorry, detectedLang.code);
                    clearTimeout(resetTimer);
                    resetTimer = setTimeout(resetToIdle, 2500);
                }
            }
        };
        activeRecognition.onerror = function () {};
        activeRecognition.onend = function () {
            if (state === "awaiting_id" && !gotFinal) {
                setPill("Sorry, I couldn't find that record", "Say \"Hi PXT\" to try again");
                speak(LANGUAGES["en"].sorry, LANGUAGES["en"].code);
                clearTimeout(resetTimer);
                resetTimer = setTimeout(resetToIdle, 2500);
            }
        };

        try { activeRecognition.start(); } catch (e) {
            clearTimeout(resetTimer);
            resetTimer = setTimeout(resetToIdle, 500);
        }
    }

    window.addEventListener("load", function () {
        bgVideo.muted = false;
        bgVideo.play().catch(function () {
            bgVideo.muted = true;
            bgVideo.play().catch(function () {});
            const retryUnmute = setInterval(function () {
                bgVideo.muted = false;
                bgVideo.play().then(function () { clearInterval(retryUnmute); }).catch(function () {});
            }, 3000);
        });
        setTimeout(initWakeRecognition, 300);
        try {
            const warm = new SpeechSynthesisUtterance(' ');
            warm.volume = 0;
            window.speechSynthesis.speak(warm);
        } catch (e) {}
    });

    window.addEventListener("beforeunload", function () {
        shouldRun = false;
        stopActiveRecognition();
        if (wakeRecognition) { try { wakeRecognition.stop(); } catch (e) {} }
    });
})();
</script>
</html>
"""

KIOSK_HTML = KIOSK_HTML.replace("__STAFF_DATA_JSON__", staff_json)
VIDEO_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner.mp4"
KIOSK_HTML = KIOSK_HTML.replace("__VIDEO_SRC__", VIDEO_URL)

st.components.v1.html(KIOSK_HTML, height=1000, scrolling=False)
