import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="PXT HR Kiosk", page_icon="🤖", layout="wide", initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; margin: 0; padding: 0; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container { padding: 0 !important; max-width: 100% !important; }
    </style>
""",
    unsafe_allow_html=True,
)

# Load Staff Data
try:
  df = pd.read_csv("staff_data.csv")
except:
  data = {
      "login_id": ["EMP001", "EMP002", "EMP003", "EMP004"],
      "name": ["Ahmed Ali", "John Doe", "Priya Sharma", "Kintu Moses"],
      "language": ["Arabic", "English", "Hindi", "Ugandan"],
      "leaves_remaining": [4, 2, 5, 3],
      "off_days": ["Friday", "Saturday", "Sunday", "Sunday"],
      "status": ["Present", "Absent", "Present", "Present"],
  }
  df = pd.DataFrame(data)

# Admin Panel Sidebar
with st.sidebar:
  st.subheader("PXT Admin Panel")
  pwd = st.text_input("Admin Password", type="password")
  if pwd == "pxt123":
    st.success("Access Granted")
    up = st.file_uploader("Update staff_data.csv", type=["csv"])
    if up:
      pd.read_csv(up).to_csv("staff_data.csv", index=False)
      st.rerun()
    st.dataframe(df)

# Kiosk HTML & JS with reliable fallback background gradient + video support
html_kiosk = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body, html {{
            margin: 0; padding: 0; width: 100vw; height: 100vh;
            background: radial-gradient(circle at center, #0B1120 0%, #000000 100%);
            overflow: hidden; font-family: 'Segoe UI', Tahoma, sans-serif; color: white;
        }}
        .video-container {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; opacity: 0.8;
        }}
        video {{ width: 100%; height: 100%; object-fit: cover; }}
        .overlay-content {{
            position: absolute; bottom: 50px; width: 100%; z-index: 10; text-align: center;
        }}
        .status-pill {{
            background: rgba(15, 23, 42, 0.9);
            border: 1px solid rgba(59, 130, 246, 0.5);
            display: inline-block; padding: 22px 45px; border-radius: 40px;
            box-shadow: 0 0 40px rgba(59, 130, 246, 0.4); backdrop-filter: blur(12px); max-width: 700px;
        }}
        h2 {{ margin: 0 0 10px 0; color: #60a5fa; font-size: 28px; text-shadow: 0 0 10px rgba(96,165,250,0.5); }}
        p {{ margin: 5px 0; font-size: 18px; color: #e2e8f0; }}
    </style>
</head>
<body>
    <div class="video-container">
        <video autoplay muted loop playsinline>
            <source src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4" type="video/mp4">
            Your browser does not support the video tag.
        </video>
    </div>

    <div class="overlay-content">
        <div class="status-pill" id="statusBox">
            <h2 id="titleText">I am your PXT AI Assistant</h2>
            <p id="subText">Say "Hi PXT" to start...</p>
        </div>
    </div>

    <script>
        const staffData = {df.to_json(orient='records')};
        const parsedStaff = JSON.parse(JSON.stringify(staffData));
        const titleText = document.getElementById('titleText');
        const subText = document.getElementById('subText');
        let isListeningForWakeWord = true;
        let recognition;

        function speak(text, lang='en-US') {{
            if ('speechSynthesis' in window) {{
                let utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = lang;
                window.speechSynthesis.speak(utterance);
            }}
        }}

        function startListening() {{
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {{
                subText.innerText = "Speech Recognition requires Google Chrome.";
                return;
            }}
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = false;
            recognition.lang = 'en-US';

            recognition.onresult = function(event) {{
                const transcript = event.results[event.results.length - 1][0].transcript.trim().toLowerCase();
                console.log("Heard: " + transcript);

                if (isListeningForWakeWord) {{
                    if (transcript.includes('pxt') || transcript.includes('hi pxt') || transcript.includes('hey pxt')) {{
                        isListeningForWakeWord = false;
                        titleText.innerText = "Listening...";
                        subText.innerText = "Kindly tell me your login or name.";
                        speak("Kindly tell me your login or name.");
                    }}
                }} else {{
                    let found = parsedStaff.find(emp => 
                        transcript.includes(emp.login_id.toLowerCase()) || 
                        transcript.includes(emp.name.toLowerCase())
                    );
                    if (found) {{
                        titleText.innerText = `Welcome, ${{found.name}} 👋`;
                        subText.innerText = `Status: ${{found.status}} | Leaves: ${{found.leaves_remaining}} | Off: ${{found.off_days}}`;
                        speak(`Hello ${{found.name}}. Your attendance status is ${{found.status}}, remaining leaves are ${{found.leaves_remaining}} days, and your next off day is ${{found.off_days}}.`);
                    }} else {{
                        titleText.innerText = "Employee Not Found";
                        subText.innerText = `No record for: "${{transcript}}"`;
                        speak("Sorry, I could not find your record.");
                    }}
                    setTimeout(() => {{
                        isListeningForWakeWord = true;
                        titleText.innerText = "I am your PXT AI Assistant";
                        subText.innerText = 'Say "Hi PXT" to start...';
                    }}, 8000);
                }}
            }};
            recognition.onerror = function(event) {{}};
            recognition.onend = function() {{ try {{ recognition.start(); }} catch(e) {{}} }};
            recognition.start();
        }}

        window.addEventListener('click', () => {{
            try {{ recognition.start(); }} catch(e) {{}}
        }}, {{ once: true }});

        setTimeout(startListening, 1000);
    </script>
</body>
</html>
"""

import streamlit.components.v1 as components

components.html(html_kiosk, height=950, scrolling=False)
