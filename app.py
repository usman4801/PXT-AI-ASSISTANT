"""
PXT Hub - AI Voice Kiosk (v4)
Serves kiosk.html via localhost to fix Chrome mic permission popup.
"""
import json, os, socket, threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import pandas as pd
import streamlit as st

APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)
CSV_PATH = "staff_data.csv"
ADMIN_PASSWORD = "pxt123"
REQUIRED_COLUMNS = ["EmployeeID", "Name", "Status", "RemainingLeaves", "NextOffDay"]
KIOSK_PORT = 8769
VIDEO_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner.mp4"

st.set_page_config(page_title="PXT Hub", page_icon="\U0001f399\ufe0f", layout="wide", initial_sidebar_state="collapsed")

def load_staff_data():
    if os.path.exists(CSV_PATH):
        try:
            df = pd.read_csv(CSV_PATH, dtype=str).fillna("")
            missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
            if missing:
                st.error(f"Missing: {', '.join(missing)}")
                return pd.DataFrame(columns=REQUIRED_COLUMNS)
            return df
        except Exception as e:
            st.error(f"CSV error: {e}")
            return pd.DataFrame(columns=REQUIRED_COLUMNS)
    return pd.DataFrame(columns=REQUIRED_COLUMNS)

def df_to_json(df):
    return json.dumps([{
        "id": str(r.get("EmployeeID","")).strip(),
        "name": str(r.get("Name","")).strip(),
        "status": str(r.get("Status","")).strip(),
        "leaves": str(r.get("RemainingLeaves","")).strip(),
        "nextoff": str(r.get("NextOffDay","")).strip(),
        "aliases": [a.strip() for a in str(r.get("Aliases","")).split("|") if a.strip()],
    } for r in df.to_dict(orient="records")], ensure_ascii=False)

def is_port_in_use(p):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", p)) == 0

class Q(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw): super().__init__(*a, directory=APP_DIR, **kw)
    def log_message(self, *_): pass

def start_server():
    if is_port_in_use(KIOSK_PORT): return
    t = threading.Thread(target=HTTPServer(("0.0.0.0", KIOSK_PORT), Q).serve_forever, daemon=True)
    t.start()

# CSS
st.markdown("""<style>
#MainMenu,footer,header{display:none!important;}
[data-testid="stToolbar"],[data-testid="stStatusWidget"],[data-testid="stDecoration"],
.viewerBadge_container,.stActionButton,#manage-app-button,
div[data-testid="manage-app-button"],[data-testid="stConnectionStatus"]{display:none!important;}
div.block-container{padding:0!important;margin:0!important;max-width:100%!important;}
html,body,[data-testid="stAppViewContainer"]{background:#05070c;overflow:hidden;}
[data-testid="stSidebar"]{background:#0a0d14;}
</style>""", unsafe_allow_html=True)

# Admin
with st.sidebar:
    st.markdown("### \U0001f512 PXT Admin")
    pwd = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Admin password")
    if pwd == ADMIN_PASSWORD:
        st.success("Access granted")
        uploaded = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed")
        if uploaded:
            try:
                new_df = pd.read_csv(uploaded, dtype=str).fillna("")
                missing = [c for c in REQUIRED_COLUMNS if c not in new_df.columns]
                if missing: st.error(f"Missing: {', '.join(missing)}")
                else: new_df.to_csv(CSV_PATH, index=False); st.success("Updated!"); st.rerun()
            except Exception as e: st.error(str(e))
        st.divider()
        st.dataframe(load_staff_data(), use_container_width=True, height=300)
    elif pwd: st.error("Wrong password")

# Build & serve
staff_df = load_staff_data()
sj = df_to_json(staff_df)

# Write kiosk.html with injected data
kiosk_path = os.path.join(APP_DIR, "kiosk.html")
with open(os.path.join(APP_DIR, "kiosk_template.html"), "r", encoding="utf-8") as f:
    tmpl = f.read()
tmpl = tmpl.replace("__STAFF__", sj).replace("__VIDEO__", VIDEO_URL)
with open(kiosk_path, "w", encoding="utf-8") as f:
    f.write(tmpl)

start_server()

st.markdown(f"""<iframe src="http://localhost:{KIOSK_PORT}/kiosk.html"
allow="microphone;autoplay;speaker" style="position:fixed;top:0;left:0;width:100vw;height:100vh;border:none;z-index:1;"></iframe>""",
unsafe_allow_html=True)
