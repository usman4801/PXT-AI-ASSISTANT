"""
PXT Hub - Full Voice Kiosk with Background Video & Theme Switcher
Single-file app (No external HTML file needed)
"""
import json
import os
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_PASSWORD = "pxt123"

# Look for data file automatically
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
# 2. ADMIN SIDEBAR (Data Upload)
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
# 4. FULL VOICE KIOSK INTERFACE WITH VIDEO & THEME SWITCHER
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
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, sans-serif; }}
        body, html {{ width: 100%; height: 100%; overflow: hidden; background: #05070c; }}
        
        /* Fullscreen Video Background */
        #bgVideo {{
            position: fixed;
            right: 0;
            bottom: 0;
            min-width: 100%;
            min-height: 100%;
            width: auto;
            height: auto;
            z-index: 1;
            object-fit: cover;
            filter: brightness(0.4) contrast(1.1);
            transition: opacity 0.5s ease-in-out;
        }}

        /* Overlay UI Content */
        .kiosk-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: 2;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: rgba(5, 7, 12, 0.35);
        }}

        /* Top-Right Theme Switcher (3 Dots) */
        .theme-switcher {{
            position: fixed;
            top: 25px;
            right: 30px;
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
            width: 14px;
            height: 14px;
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

        /* Main Glassmorphism Kiosk Card */
        .card {{
            background: rgba(15, 23, 42, 0.75);
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
        p.subtitle {{ color: #cbd5e1; margin-bottom: 30px; font-size: 1.05rem; }}

        /* Voice Mic Button */
        .mic-btn {{
            background: linear-gradient(135deg, #0284c7, #2563eb);
            border: none;
            width: 105px;
            height: 105px;
            border-radius: 50%;
            color: white;
            font-size: 2.8rem;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 0 25px rgba(2, 132, 199, 0.5);
            margin-bottom: 20px;
            outline: none;
        }}

        .mic-btn:hover {{ transform: scale(1.06); }}
        .mic-btn.listening {{
            background: linear-gradient(135deg, #dc2626, #ef4444);
            animation: pulse 1.5s infinite;
        }}

        @keyframes pulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }}
            70% {{ box-shadow: 0 0 0 22px rgba(239, 68, 68, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }}
        }}

        .status {{ font-size: 1.15rem; color: #38bdf8; min-height: 28px; margin-bottom: 15px; font-weight: 500; }}

        /* Result Panel */
        .result-box {{
            background: rgba(30, 41, 59, 0.85);
            border-radius: 16px;
            padding: 22px;
            text-align: left;
            margin-top: 20px;
            display: none;
            border: 1px solid rgba(255, 255, 255, 0.08);
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
    </style>
</head>
<body>

    <!-- Video Background -->
    <video autoplay muted loop id="bgVideo">
        <source src="banner.mp4" type="video/mp4">
    </video>

    <!-- Top-Right Theme Dots -->
    <div class="theme-switcher">
        <div class="theme-dot dot-theme1 active" title="Theme 1 (banner.mp4)" onclick="switchTheme('banner.mp4', this)"></div>
        <div class="theme-dot dot-theme2" title="Theme 2 (banner2.mp4)" onclick="switchTheme('banner2.mp4', this)"></div>
        <div class="theme-dot dot-theme3" title="Theme 3 (banner3.mp4)" onclick="switchTheme('banner3.mp4', this)"></div>
    </div>

    <!-- Kiosk Content -->
    <div class="kiosk-overlay">
        <div class="card">
            <h1>🎙️ PXT Hub</h1>
            <p class="subtitle">Tap microphone or say <b>"Hi PXT"</b> to check your details.</p>
            
            <button class="mic-btn" id="micBtn" onclick="toggleListening()">🎤</button>
            <div class="status" id="statusText">Tap mic to speak</div>

            <div class="result-box" id="resultBox">
                <div class="result-item">👤 Name: <span class="highlight" id="resName">-</span></div>
                <div class="result-item">🆔 Badge ID: <span class="highlight" id="resId">-</span></div>
                <div class="result-item">📋 Shift / Status: <span class="highlight" id="resStatus">-</span></div>
                <div class="result-item">🌴 Remaining Leaves: <span class="highlight" id="resLeaves">-</span></div>
                <div class="result-item">📅 Next Off Day: <span class="highlight" id="resOff">-</span></div>
            </div>
        </div>
    </div>

<script>
    const staffData = {staff_json};
    let recognition;
    let isListening = false;

    // Theme Switcher
    function switchTheme(videoSrc, dotElem) {{
        const video = document.getElementById('bgVideo');
        video.src = videoSrc;
        video.play();
        
        document.querySelectorAll('.theme-dot').forEach(d => d.classList.remove('active'));
        dotElem.classList.add('active');
    }}

    // Speech Recognition
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {{
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onresult = function(event) {{
            const transcript = event.results[event.results.length - 1][0].transcript.trim().toLowerCase();
            document.getElementById('statusText').innerText = 'Heard: "' + transcript + '"';
            processVoiceCommand(transcript);
        }};

        recognition.onerror = function(event) {{
            document.getElementById('statusText').innerText = 'Microphone Error. Tap to Retry.';
            stopListening();
        }};
    }} else {{
        document.getElementById('statusText').innerText = 'Voice search not supported in this browser.';
    }}

    function toggleListening() {{
        if (isListening) {{
            stopListening();
        }} else {{
            startListening();
        }}
    }}

    function startListening() {{
        if (!recognition) return;
        try {{
            recognition.start();
            isListening = true;
            document.getElementById('micBtn').classList.add('listening');
            document.getElementById('statusText').innerText = 'Listening... Say your Name or Badge ID';
        }} catch(e) {{}}
    }}

    function stopListening() {{
        if (!recognition) return;
        try {{
            recognition.stop();
            isListening = false;
            document.getElementById('micBtn').classList.remove('listening');
        }} catch(e) {{}}
    }}

    function processVoiceCommand(text) {{
        let query = text.replace('hi pxt', '').replace('pxt', '').trim();
        
        let found = staffData.find(emp => 
            (emp.id && query.includes(emp.id.toLowerCase())) ||
            (emp.name && query.includes(emp.name.toLowerCase())) ||
            (emp.alias && query.includes(emp.alias.toLowerCase()))
        );

        if (found) {{
            showEmployeeDetails(found);
            speakResponse("Hello " + found.name + ". Your status is " + found.status + " and your next off is " + found.next_off);
        }} else if (query.length > 2) {{
            speakResponse("Sorry, I could not find employee details for " + query);
        }}
    }}

    function showEmployeeDetails(emp) {{
        document.getElementById('resName').innerText = emp.name || 'N/A';
        document.getElementById('resId').innerText = emp.id || 'N/A';
        document.getElementById('resStatus').innerText = emp.status || 'N/A';
        document.getElementById('resLeaves').innerText = emp.leaves || 'N/A';
        document.getElementById('resOff').innerText = emp.next_off || 'N/A';
        document.getElementById('resultBox').style.display = 'block';
    }}

    function speakResponse(text) {{
        if ('speechSynthesis' in window) {{
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.9;
            window.speechSynthesis.speak(utterance);
        }}
    }}
</script>
</body>
</html>
"""

components.html(kiosk_html_code, height=900, scrolling=False)
