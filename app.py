import pandas as pd
import streamlit as st

# Page Configuration for Fullscreen Kiosk Mode
st.set_page_config(
    page_title="PXT HR Kiosk", page_icon="🤖", layout="wide"
)

# Custom CSS for Sleek Dark Theme, Glowing AI Face Look & Hidden Top Admin Bar
st.markdown(
    """
    <style>
    .stApp {
        background-color: #05050A;
        color: #FFFFFF;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    /* Hide Streamlit default header and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Top Hidden/Discreet Admin Bar Styling */
    .admin-bar {
        background: rgba(255, 255, 255, 0.03);
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding: 8px 20px;
        display: flex;
        justify-content: flex-end;
        gap: 15px;
        border-radius: 0 0 10px 10px;
    }
    
    /* Glowing AI Avatar container */
    .ai-container {
        text-align: center;
        padding: 20px;
    }
    
    .status-box {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(59, 130, 246, 0.3);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.2);
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- TOP DISCREET ADMIN MENU ---
with st.container():
  col1, col2 = st.columns([8, 2])
  with col2:
    with st.popover("⚙️ Admin Settings"):
      st.subheader("PXT Control Panel")
      admin_pass = st.text_input("Admin Password", type="password")
      if admin_pass == "pxt123":  # Default temporary password
        st.success("Access Granted")
        uploaded_file = st.file_uploader("Upload Staff CSV", type=["csv"])
        if uploaded_file is not None:
          df_admin = pd.read_csv(uploaded_file)
          df_admin.to_csv("staff_data.csv", index=False)
          st.rerun()
      elif admin_pass:
        st.error("Incorrect Password")

# --- MAIN KIOSK INTERFACE ---
st.markdown(
    """
    <div class="ai-container">
        <h1>PXT HR Assistant</h1>
        <p style="color: #94a3b8;">Simply say 'Hi PXT' or enter your Login ID below to get details in your native language.</p>
    </div>
""",
    unsafe_allow_html=True,
)

# Load Staff Database
try:
  df = pd.read_csv("staff_data.csv")
except:
  # Fallback sample data if file missing
  data = {
      "login_id": ["EMP001", "EMP002", "EMP003", "EMP004"],
      "name": ["Ahmed Ali", "John Doe", "Priya Sharma", "Kintu Moses"],
      "language": ["Arabic", "English", "Hindi", "Ugandan"],
      "leaves_remaining": [4, 2, 5, 3],
      "off_days": ["Friday", "Saturday", "Sunday", "Sunday"],
      "status": ["Present", "Absent", "Present", "Present"],
  }
  df = pd.DataFrame(data)

# Interactive Input Simulation for Kiosk (Voice / Text Entry)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
  user_input = st.text_input(
      "🎙️ Listening... (Type your Login ID or Name)",
      placeholder="e.g. EMP001 or Ahmed Ali",
  )

  if user_input:
    # Search for employee by ID or Name (case-insensitive)
    result = df[
        (df["login_id"].str.lower() == user_input.strip().lower())
        | (df["name"].str.lower().str.contains(user_input.strip().lower()))
    ]

    if not result.empty:
      emp = result.iloc[0]
      st.markdown(
          f"""
            <div class="status-box">
                <h3>Welcome, {emp['name']} 👋</h3>
                <p><b>Language Detected:</b> {emp['language']}</p>
                <p><b>Attendance Status:</b> <span style="color: #22c55e;">{emp['status']}</span></p>
                <p><b>Remaining Leaves:</b> {emp['leaves_remaining']} Days</p>
                <p><b>Next Off Day:</b> {emp['off_days']}</p>
            </div>
            """,
          unsafe_allow_html=True,
      )

      # Multi-language voice text response simulation
      if emp["language"] == "Arabic":
        msg = f"مرحباً {emp['name']}. رصيد إجازاتك المتبقية هو {emp['leaves_remaining']} أيام."
      elif emp["language"] == "Hindi":
        msg = f"नमस्ते {emp['name']}. आपकी शेष छुट्टियां {emp['leaves_remaining']} दिन हैं।"
      else:
        msg = f"Hello {emp['name']}. Your remaining leaves are {emp['leaves_remaining']} days."

      st.info(f"🔊 Assistant Audio Response ({emp['language']}): {msg}")

    else:
      st.error(
          "Employee not found. Please check your Login ID and try speaking"
            " again."
      )

# Footer info
st.markdown(
    """
    <hr style="border-color: rgba(255,255,255,0.05); margin-top: 50px;">
    <div style="display: flex; justify-content: space-between; color: #64748b; font-size: 12px;">
        <span>🔒 Global Staff Status: Online</span>
        <span>Secure PXT Portal</span>
    </div>
""",
    unsafe_allow_html=True,
)
