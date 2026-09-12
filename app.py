"""
PXT Hub - Interactive Voice Kiosk
Single-File Streamlit Application
"""
import json
import os
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_PASSWORD = "pxt123"

# Data file path setup
data_file_path = os.path.join(APP_DIR, "data.xlsx")
if not os.path.exists(data_file_path):
    data_file_path = os.path.join(APP_DIR, "data.csv")

st.set_page_config(
    page_title="PXT Hub Kiosk",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# 1. DATA LOADING FUNCTION
# ---------------------------------------------------------
def load_staff_data():
    if not os.path.exists(data_file_path):
        return []
    try:
        if data_file_path.endswith(".csv"):
            df = pd.read_csv(data_file_path, dtype=str).fillna("")
        else:
            df = pd.read_excel(data_file_path, dtype=str, engine="openpyxl").fillna("")
            
        records = []
        for _, r in df.iterrows():
            badge = str(r.get("EmployeeID", r.get("Badge ID", ""))).strip()
            if not badge or badge.lower() == "nan": 
                continue
            records.append({
                "id": badge,
                "name": str(r.get("Name", r.get("Employee Name", ""))).strip(),
                "status": str(r.get("Status", r.get("Shift", ""))).strip(),
                "leaves": str(r.get("RemainingLeaves", "")).strip(),
                "next_off": str(r.get("NextOffDay", r.get("week off", ""))).strip(),
                "alias": str(r.get("Aliases", "")).strip(),
            })
        return records
    except Exception:
        return []

# ---------------------------------------------------------
# 2. ADMIN SIDEBAR
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### 🔒 PXT Admin")
    pwd = st.text_input("Password", type="password", placeholder="Admin password")
    if pwd == ADMIN_PASSWORD:
        st.success("Access Granted")
        uploaded = st.file_uploader("Upload data.xlsx or data.csv", type=["xlsx", "csv"])
        if uploaded:
            try:
                target_file = "data.xlsx" if uploaded.name.endswith(".xlsx") else "data.csv"
                save_path = os.path.join(APP_DIR, target_file)
                with open(save_path, "wb") as f:
                    f.write(uploaded.read())
                st.success("Data uploaded successfully!")
                st.rerun()
            except Exception as e:
                st.error(str(e))
        
        staff_list = load_staff_data()
        st.caption(f"{len(staff_list)} staff records loaded.")
        if staff_list:
            st.dataframe(pd.DataFrame(staff_list), use_container_width=True)

# ---------------------------------------------------------
# 3. HIDE STREAMLIT UI CHROME
# ---------------------------------------------------------
st.markdown("""
<style>
#MainMenu, footer, header {display:none !important;}
[data-testid="stToolbar"], [data-testid="stStatusWidget"], [data-testid="stDecoration"] {display:none !important;}
div.block-container {padding: 0 !important; margin: 0 !important; max-width: 100% !important;}
html, body, [data-testid="stAppViewContainer"] {background: #000000; overflow: hidden;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. KIOSK INTERFACE COMPONENT
# ---------------------------------------------------------
staff_data = load_staff_data()
staff_json = json.dumps(staff_data, ensure_ascii=False)

kiosk_html_code = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
        body, html {{ width: 100%; height: 100%; overflow: hidden; background: #030508; color: #ffffff; }}
        
        /* Ambient Glow & Video Fallback Background */
        .background-container {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: 1;
            background: radial-gradient(circle at 50% 30%, rgba(30, 58, 138, 0.35) 0%, rgba(3, 5, 8, 0.95) 75%);
            overflow: hidden;
        }}
        #bgVideo {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center center;
            filter: brightness(0.65) contrast(1.1);
        }}

        .kiosk-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: 2;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 40px 60px;
        }}

        /* Header Bar */
        .header-bar {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            width: 100%;
        }}
        .greeting-container {{ display: flex; flex-direction: column; gap: 6px; }}
        .greeting-title {{ font-size: 2.2rem; font-weight: 700; color: #ffffff; letter-spacing: -0.3px; }}
        .greeting-sub {{ font-size: 1.15rem; color: #94a3b8; font-weight: 400; }}
        
        .continue-btn {{
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 30px;
            padding: 12px 24px;
            color: #ffffff;
            font-size: 0.95rem;
            display: flex;
            align-items: center;
            gap: 10px;
            backdrop-filter: blur(12px);
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        .continue-btn:hover {{ background: rgba(255, 255, 255, 0.2); }}

        /* Main Center Content */
        .center-content {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            margin-top: auto;
            margin-bottom: auto;
        }}
        .main-title {{
            font-size: 3.4rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 10px;
            letter-spacing: -0.5px;
        }}
        .highlight-ai {{
            background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .sub-instruction {{ font-size: 1.25rem; color: #94a3b8; margin-bottom: 35px; font-weight: 400; }}

        /* Interactive Mic Button & Sound Wave Ring */
        .mic-wrapper {{
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
        }}
        
        .mic-box {{
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: linear-gradient(135deg, #1e3a8a, #0f172a);
            border: 2px solid rgba(56, 189, 248, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            color: #38bdf8;
            box-shadow: 0 0 25px rgba(56, 189, 248, 0.3);
            transition: all 0.3s ease;
            z-index: 5;
        }}

        .wave-ring {{
            position: absolute;
            width: 80px;
            height: 80px;
            border-radius: 50%;
            border: 2px solid rgba(56, 189, 248, 0.6);
            opacity: 0;
            z-index: 4;
            pointer-events: none;
        }}

        .active-speech .mic-box {{
            background: linear-gradient(135deg, #0284c7, #2563eb);
            color: #ffffff;
            border-color: #60a5fa;
            box-shadow: 0 0 40px rgba(37, 99, 235, 0.8);
        }}

        .active-speech .wave-ring {{
            animation: ripple-wave 1.5s infinite cubic-bezier(0, 0.2, 0.8, 1);
        }}
        .active-speech .wave-ring:nth-child(2) {{ animation-delay: 0.4s; }}
        .active-speech .wave-ring:nth-child(3) {{ animation-delay: 0.8s; }}

        @keyframes ripple-wave {{
            0% {{ transform: scale(1); opacity: 0.8; border-color: #38bdf8; }}
            100% {{ transform: scale(2.4); opacity: 0; border-color: #818cf8; }}
        }}

        .status-text {{
            font-size: 1.15rem;
            color: #38bdf8;
            margin-top: 20px;
            font-weight: 500;
            min-height: 28px;
        }}

        /* Staff Result Panel */
        .result-box {{
            background: rgba(15, 23, 42, 0.9);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 20px;
            padding: 25px 35px;
            width: 100%;
            max-width: 520px;
            margin-top: 25px;
            display: none;
            text-align: left;
            box-shadow: 0 20px 40px rgba(0,0,0,0.6);
        }}
        .result-row {{ display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 1.05rem; color: #cbd5e1; }}
        .result-row:last-child {{ margin-bottom: 0; }}
        .val-text {{ color: #fbbf24; font-weight: 600; }}

        /* Footer */
        .footer-bar {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            color: #64748b;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body onclick="enableAudioAndListen()">

    <!-- Ambient / Video Container -->
    <div class="background-container">
        <video autoplay muted loop id="bgVideo" onerror="this.style.display='none'">
            <source src="banner.mp4" type="video/mp4">
        </video>
    </div>

    <!-- Interface -->
    <div class="kiosk-overlay">
        <!-- Top Bar -->
        <div class="header-bar">
            <div class="greeting-container">
                <div class="greeting-title" id="greetingTitle">Good Evening 👋</div>
                <div class="greeting-sub">How can I help you today?</div>
            </div>
            <div class="continue-btn">
                <span>💬</span> Continue chat
            </div>
        </div>

        <!-- Center Content -->
        <div class="center-content">
            <h1 class="main-title">I'm Your PXT <span class="highlight-ai">AI</span> Assistant</h1>
            <p class="sub-instruction">You can ask me anything or give a command.</p>

            <div class="mic-wrapper" id="micWrapper" onclick="toggleListening(event)">
                <div class="wave-ring"></div>
                <div class="wave-ring"></div>
                <div class="wave-ring"></div>
                <div class="mic-box" id="micIcon">🎙️</div>
            </div>
            
            <div class="status-text" id="statusText">Click anywhere or tap mic to activate voice...</div>

            <!-- Details Display Panel -->
            <div class="result-box" id="resultBox">
                <div class="result-row"><span>👤 Employee Name:</span><span class="val-text" id="resName">-</span></div>
                <div class="result-row"><span>🆔 Badge ID:</span><span class="val-text" id="resId">-</span></div>
                <div class="result-row"><span>📋 Shift / Status:</span><span class="val-text" id="resStatus">-</span></div>
                <div class="result-row"><span>📅 Next Off Day:</span><span class="val-text" id="resOff">-</span></div>
            </div>
        </div>

        <!-- Bottom Footer -->
        <div class="footer-bar">
            <span>🔒 Your data is secure and protected</span>
            <span>|</span>
            <span>Powered by Next-Gen AI ✨</span>
        </div>
    </div>

<script>
    const staffData = {staff_json};
    let recognition;
    let autoResetTimer = null;
    let isListening = false;

    function setDynamicGreeting() {{
        const hour = new Date().getHours();
        let greeting = "Good Morning 👋";
        if (hour >= 12 && hour < 17) {{
            greeting = "Good Afternoon 👋";
        }} else if (hour >= 17) {{
            greeting = "Good Evening 👋";
        }}
        document.getElementById('greetingTitle').innerText = greeting;
    }}

    function enableAudioAndListen() {{
        if (!isListening) {{
            startListening();
        }}
    }}

    function toggleListening(e) {{
        if (e) e.stopPropagation();
        if (isListening) {{
            stopListening();
        }} else {{
            startListening();
        }}
    }}

    function startListening() {{
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {{
            document.getElementById('statusText').innerText = 'Browser voice recognition not supported.';
            return;
        }}

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = function() {{
            isListening = true;
            document.getElementById('micWrapper').classList.add('active-speech');
            document.getElementById('statusText').innerText = 'Listening... Speak Badge ID or Name';
        }};

        recognition.onresult = function(event) {{
            let currentText = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {{
                currentText += event.results[i][0].transcript;
            }}
            currentText = currentText.trim().toLowerCase();

            if (currentText.length > 0) {{
                document.getElementById('statusText').innerText = '"' + currentText + '"';
                processQuery(currentText);
            }}
        }};

        recognition.onerror = function() {{
            document.getElementById('statusText').innerText = 'Mic error. Retrying...';
        }};

        recognition.onend = function() {{
            if (isListening) {{
                try {{ recognition.start(); }} catch(e) {{}}
            }}
        }};

        try {{ recognition.start(); }} catch(e) {{}}
    }}

    function stopListening() {{
        isListening = false;
        if (recognition) recognition.stop();
        document.getElementById('micWrapper').classList.remove('active-speech');
        document.getElementById('statusText').innerText = 'Microphone paused. Tap mic to start.';
    }}

    function processQuery(text) {{
        let query = text.toLowerCase().trim();
        if (query.length < 2) return;

        let found = staffData.find(emp => 
            (emp.id && query.includes(emp.id.toLowerCase())) ||
            (emp.name && query.includes(emp.name.toLowerCase())) ||
            (emp.alias && query.includes(emp.alias.toLowerCase()))
        );

        if (found) {{
            showDetails(found);
            speakResponse("Hello " + found.name + ". Your status is " + found.status + " and your next off day is " + found.next_off);
            
            clearTimeout(autoResetTimer);
            autoResetTimer = setTimeout(() => {{
                resetKiosk();
            }}, 8000);
        }}
    }}

    function showDetails(emp) {{
        document.getElementById('resName').innerText = emp.name || 'N/A';
        document.getElementById('resId').innerText = emp.id || 'N/A';
        document.getElementById('resStatus').innerText = emp.status || 'N/A';
        document.getElementById('resOff').innerText = emp.next_off || 'N/A';
        document.getElementById('resultBox').style.display = 'block';
    }}

    function resetKiosk() {{
        document.getElementById('resultBox').style.display = 'none';
        document.getElementById('statusText').innerText = 'Listening... Speak Badge ID or Name';
    }}

    function speakResponse(text) {{
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.95;
            window.speechSynthesis.speak(utterance);
        }}
    }}

    window.onload = function() {{
        setDynamicGreeting();
    }};
</script>
</body>
</html>
"""

components.html(kiosk_html_code, height=900, scrolling=False)
