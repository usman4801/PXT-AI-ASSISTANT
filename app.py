"""
PXT Hub - AI Voice Kiosk
Serves kiosk on localhost. Reads staff data from data.xlsx (Roster sheet).
"""
import json, os, socket, threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import pandas as pd
import streamlit as st

APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)
ADMIN_PASSWORD = "pxt123"
KIOSK_PORT = 8769
VIDEO_URL = "banner.mp4"
DATA_FILE = "data.xlsx"

st.set_page_config(page_title="PXT Hub", page_icon="\U0001f399\ufe0f", layout="wide", initial_sidebar_state="collapsed")

def load_staff_data():
    if not os.path.exists(DATA_FILE):
        st.warning("data.xlsx not found in PXT_Hub folder")
        return []
    try:
        df = pd.read_excel(DATA_FILE, sheet_name="Roster", dtype=str).fillna("")
        records = []
        for _, r in df.iterrows():
            badge = str(r.get("Badge ID","")).strip().split(".")[0]  # remove .0
            if not badge or badge.lower() == "nan": continue
            company = str(r.get("agency",r.get("3P",""))).strip()
            if company == "QuessCorp": company = "Quesscorp"  # normalize
            records.append({
                "id": badge,
                "name": str(r.get("Employee Name","")).strip(),
                "shift": str(r.get("Shift","")).strip(),
                "off1": str(r.get("week off",r.get("OFF1",""))).strip(),
                "off2": str(r.get("week off 2",r.get("OFF2",""))).strip(),
                "dept": str(r.get("Department","")).strip(),
                "company": company,
                "manager": str(r.get("Manager",r.get("Line Manager",""))).strip(),
                "doj": str(r.get("date of joining",r.get("DOJ",""))).strip()[:10],
                "phone": str(r.get("Phone number","")).strip(),
                "birthday": str(r.get("Birthday Month","")).strip(),
                "hours": str(r.get("Working Hours","")).strip(),
                "shift_time": str(r.get("Shift Timings","")).strip(),
                "pickup": str(r.get("Pickup point","")).strip(),
                "email": str(r.get("Email address","")).strip(),
                "country": str(r.get("Home county","")).strip(),
                "tenure_end": str(r.get("Tenure end","")).strip()[:10],
                "language": str(r.get("Language ","")).strip(),
            })
        return records
    except Exception as e:
        st.error(f"Error reading data.xlsx: {e}")
        return []

class Q(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw): super().__init__(*a, directory=APP_DIR, **kw)
    def log_message(self, *_): pass

def is_port_in_use(p):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", p)) == 0

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
        uploaded = st.file_uploader("Upload new data.xlsx", type=["xlsx"], label_visibility="collapsed")
        if uploaded:
            try:
                with open(DATA_FILE, "wb") as f: f.write(uploaded.read())
                st.success("Updated!"); st.rerun()
            except Exception as e: st.error(str(e))
        st.divider()
        staff = load_staff_data()
        st.caption(f"{len(staff)} employees loaded")
        if staff:
            st.dataframe(pd.DataFrame(staff).head(20), use_container_width=True, height=300)
    elif pwd: st.error("Wrong password")

# Build kiosk
staff = load_staff_data()
sj = json.dumps(staff, ensure_ascii=False)

kiosk_path = os.path.join(APP_DIR, "kiosk.html")
tmpl_path = os.path.join(APP_DIR, "kiosk_template.html")
if os.path.exists(tmpl_path):
    with open(tmpl_path, "r", encoding="utf-8") as f: tmpl = f.read()
    tmpl = tmpl.replace("__STAFF__", sj).replace("__VIDEO__", VIDEO_URL)
    with open(kiosk_path, "w", encoding="utf-8") as f: f.write(tmpl)

start_server()

st.markdown(f"""<iframe src="http://localhost:{KIOSK_PORT}/kiosk.html"
allow="microphone;autoplay" style="position:fixed;top:0;left:0;width:100vw;height:100vh;border:none;z-index:1;"></iframe>""",
unsafe_allow_html=True)
