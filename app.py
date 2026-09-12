"""
PXT Hub - Employee Shift & Staff Search App
Native Streamlit UI (No Kiosk HTML)
"""
import os
import pandas as pd
import streamlit as st

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_PASSWORD = "pxt123"
DATA_FILE = os.path.join(APP_DIR, "data.csv")

st.set_page_config(
    page_title="PXT Hub",
    page_icon="🎙️",
    layout="wide"
)

# ---------------------------------------------------------
# 1. DATA LOADING FUNCTION
# ---------------------------------------------------------
def load_staff_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame()
    try:
        if DATA_FILE.endswith(".csv"):
            df = pd.read_csv(DATA_FILE, dtype=str).fillna("")
        else:
            df = pd.read_excel(DATA_FILE, dtype=str, engine="openpyxl").fillna("")
        return df
    except Exception as e:
        st.error(f"Error loading staff data: {e}")
        return pd.DataFrame()

# ---------------------------------------------------------
# 2. ADMIN SIDEBAR
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### 🔒 PXT Admin")
    pwd = st.text_input("Password", type="password", placeholder="Admin password")
    if pwd == ADMIN_PASSWORD:
        st.success("Access Granted")
        uploaded = st.file_uploader("Upload data.csv or data.xlsx", type=["csv", "xlsx"])
        if uploaded:
            try:
                file_path = os.path.join(APP_DIR, "data.csv" if uploaded.name.endswith(".csv") else "data.xlsx")
                with open(file_path, "wb") as f:
                    f.write(uploaded.read())
                st.success("File uploaded successfully!")
                st.rerun()
            except Exception as e:
                st.error(str(e))
        
        df_staff = load_staff_data()
        st.caption(f"{len(df_staff)} staff records loaded.")

# ---------------------------------------------------------
# 3. MAIN DASHBOARD & VOICE / TEXT SEARCH
# ---------------------------------------------------------
st.title("🎙️ PXT Hub - Staff Search")
st.write("Search employee shift details by Name, Employee ID, or Status.")

df = load_staff_data()

if not df.empty:
    search_query = st.text_input("🔍 Search Employee (Name or Badge ID):", "").strip().lower()

    if search_query:
        # Filter matching rows across all columns
        mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(search_query).any(), axis=1)
        filtered_df = df[mask]

        if not filtered_df.empty:
            st.subheader("Matching Employee Records:")
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.warning(f"No employee found matching '{search_query}'.")
    else:
        st.subheader("All Staff Data:")
        st.dataframe(df, use_container_width=True)
else:
    st.info("No data file found. Please upload `data.csv` or `data.xlsx` from the Admin sidebar.")
