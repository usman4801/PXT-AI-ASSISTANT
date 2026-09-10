"""
PXT Hub - AI Voice Kiosk (v4)
Fixed for Streamlit Cloud deployment
"""
import json
import os
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Paths
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(APP_DIR, "staff_data.csv")
TEMPLATE_PATH = os.path.join(APP_DIR, "kiosk_template.html")

ADMIN_PASSWORD = "pxt123"
REQUIRED_COLUMNS = ["EmployeeID", "Name", "Status", "RemainingLeaves", "NextOffDay"]
VIDEO_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner.mp4"

# Page configuration
st.set_page_config(
    page_title="PXT Hub",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def load_staff_data():
    """Load and validate staff data from CSV"""
    if os.path.exists(CSV_PATH):
        try:
            df = pd.read_csv(CSV_PATH, dtype=str).fillna("")
            missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
            if missing:
                st.error(f"Missing required columns in CSV: {', '.join(missing)}")
                return pd.DataFrame(columns=REQUIRED_COLUMNS)
            return df
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
            return pd.DataFrame(columns=REQUIRED_COLUMNS)
    return pd.DataFrame(columns=REQUIRED_COLUMNS)

def df_to_json(df):
    """Convert dataframe rows to JSON array"""
    records = []
    for r in df.to_dict(orient="records"):
        records.append({
            "id": str(r.get("EmployeeID", "")).strip(),
            "name": str(r.get("Name", "")).strip(),
            "status": str(r.get("Status", "")).strip(),
            "leaves": str(r.get("RemainingLeaves", "")).strip(),
            "nextoff": str(r.get("NextOffDay", "")).strip(),
            "aliases": [a.strip() for a in str(r.get("Aliases", "")).split("|") if a.strip()],
        })
    return json.dumps(records, ensure_ascii=False)

# Custom Styling to hide default Streamlit chrome
st.markdown("""
<style>
#MainMenu, footer, header { display: none !important; }
[data-testid="stToolbar"], [data-testid="stStatusWidget"], [data-testid="stDecoration"],
.viewerBadge_container, .stActionButton, #manage-app-button,
div[data-testid="manage-app-button"], [data-testid="stConnectionStatus"] { display: none !important; }
div.block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
html, body, [data-testid="stAppViewContainer"] { background: #05070c; overflow: hidden; }
[data-testid="stSidebar"] { background: #0a0d14; }
iframe { width: 100vw !important; height: 100vh !important; border: none !important; }
</style>
""", unsafe_allow_html=True)

# Admin Sidebar
with st.sidebar:
    st.markdown("### 🔒 PXT Admin")
    pwd = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Admin password")
    if pwd == ADMIN_PASSWORD:
        st.success("Access granted")
        uploaded = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed")
        if uploaded:
            try:
                new_df = pd.read_csv(uploaded, dtype=str).fillna("")
                missing = [c for c in REQUIRED_COLUMNS if c not in new_df.columns]
                if missing:
                    st.error(f"Missing columns: {', '.join(missing)}")
                else:
                    new_df.to_csv(CSV_PATH, index=False)
                    st.success("Updated successfully!")
                    st.rerun()
            except Exception as e:
                st.error(str(e))
        st.divider()
        st.dataframe(load_staff_data(), use_container_width=True, height=300)
    elif pwd:
        st.error("Wrong password")

# Read Data
staff_df = load_staff_data()
sj = df_to_json(staff_df)

# Check and Render HTML Template
if not os.path.exists(TEMPLATE_PATH):
    st.error(f"⚠️ Template file missing: `{TEMPLATE_PATH}`. Please upload `kiosk_template.html` to your GitHub repo root folder.")
else:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        tmpl = f.read()

    # Dynamic data injection
    rendered_html = tmpl.replace("__STAFF__", sj).replace("__VIDEO__", VIDEO_URL)

    # Render directly via Streamlit iframe
    components.html(rendered_html, height=1000, scrolling=False)
