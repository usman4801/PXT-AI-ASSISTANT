"""
PXT Hub - AI Voice Kiosk
Serves kiosk UI directly without HTTP Server (Streamlit Cloud Compatible)
"""
import json, os
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)
ADMIN_PASSWORD = "pxt123"
VIDEO_URL = "banner.mp4"
DATA_FILE = "data.xlsx"

st.set_page_config(page_title="PXT Hub", page_icon="🎙️", layout="wide", initial_sidebar_state="collapsed")

def load_staff_data():
    if not os.path.exists(DATA_FILE):
        st.warning("data.xlsx not found in project folder")
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

# Hide Streamlit Default UI
st.markdown("""<style>
#MainMenu,footer,header{display:none!important;}
[data-testid="stToolbar"],[data-testid="stStatusWidget"],[data-testid="stDecoration"],
.viewerBadge_container,.stActionButton,#manage-app-button,
div[data-testid="manage-app-button"],[data-testid="stConnectionStatus"]{display:none!important;}
div.block-container{padding:0!important;margin:0!important;max-width:100%!important;}
html,body,[data-testid="stAppViewContainer"]{background:#05070c;overflow:hidden;}
[data-testid="stSidebar"]{background:#0a0d14;}
</style>""", unsafe_allow_html=True)

# Admin Panel
with st.sidebar:
    st.markdown("### 🔒 PXT Admin")
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

# Load Data and Prepare Template
staff = load_staff_data()
sj = json.dumps(staff, ensure_ascii=False)

tmpl_path = os.path.join(APP_DIR, "kiosk_template.html")
html_content = ""

if os.path.exists(tmpl_path):
    with open(tmpl_path, "r", encoding="utf-8") as f:
        tmpl = f.read()
    html_content = tmpl.replace("__STAFF__", sj).replace("__VIDEO__", VIDEO_URL)
else:
    html_content = "<h2>kiosk_template.html missing!</h2>"

# Render directly using Streamlit HTML component
components.html(html_content, height=1000, scrolling=False)
