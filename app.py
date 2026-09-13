"""
PXT Hub - Amazon Canopy & Tablet Ready Voice Kiosk (English Only)
Single-file Streamlit App - No external HTML template file needed.

This merges the working kiosk frontend (wake-word "Hi PXT", badge login,
staff lookup, glassmorphism UI, mic/voice setup screen, sleep/wake cycle)
directly into this one app.py. Multi-language support has been removed -
the kiosk now always greets and responds in English.

CHANGELOG (this revision):
1) Login is now badge-number ONLY. The kiosk no longer guesses a name
   from whatever it heard - if no valid badge is given, it politely
   re-asks instead of logging someone in under a misheard name. A
   20-25s "wake timeout" also puts the kiosk back to sleep if nobody
   enters a badge in time. While waiting for a badge, "who are you" /
   "what can you do" (and the same after logging in) get the same
   PXT AI Assistant introduction, answered directly without needing a login.
2) Background theme video(s) are now embedded as base64 data URIs
   instead of a plain relative <video src>. Streamlit's components.html
   renders the kiosk inside a sandboxed iframe, so a relative filename
   like "banner.mp4" never actually resolved to the file on disk - that
   was why the banner video wasn't appearing. Data URIs always work.
3) Any theme video file placed next to app.py (banner.mp4, banner2.mp4,
   banner3.mp4, ...) is auto-detected and gets a small switch-dot in the
   kiosk's top-right corner. Add more just by dropping the file in.
"""
import base64
import json
import os
import re

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ----------------------------------------------------------------------
# 0. CONFIG
# ----------------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_PASSWORD = "pxt123"  # NOTE: for production, move this to st.secrets

st.set_page_config(
    page_title="PXT Hub Kiosk",
    page_icon=" ",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def resolve_data_file() -> str:
    """data.xlsx ko priority deta hai, warna data.csv dhoondta hai."""
    xlsx_path = os.path.join(APP_DIR, "data.xlsx")
    csv_path = os.path.join(APP_DIR, "data.csv")
    if os.path.exists(xlsx_path):
        return xlsx_path
    return csv_path


DATA_FILE = resolve_data_file()


def _norm(s) -> str:
    """Lowercase and strip everything except letters/digits, so 'Badge ID',
    'BadgeID', 'badge_id' and 'Badge  ID' all compare equal."""
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _colmap(df) -> dict:
    """Map of normalized column name -> actual column name, for this dataframe."""
    return {_norm(c): c for c in df.columns}


def _pick_best_sheet(path: str):
    """An uploaded workbook may have several tabs (pivot/summary tabs, a
    'Roster' tab, termination-code lookups, etc.) - only one of which is
    the actual staff list. Score each sheet by how many of the columns we
    actually need it has, and use the best match instead of blindly
    reading whichever sheet happens to be first."""
    try:
        xls = pd.ExcelFile(path, engine="openpyxl")
    except Exception:
        return None
    signal_cols = ["badgeid", "employeeid", "employeename", "name", "shift", "department"]
    best_name, best_score = None, -1
    for name in xls.sheet_names:
        try:
            preview = xls.parse(name, dtype=str, nrows=5)
        except Exception:
            continue
        cols_norm = {_norm(c) for c in preview.columns.astype(str)}
        score = sum(1 for c in signal_cols if c in cols_norm)
        if ("badgeid" in cols_norm or "employeeid" in cols_norm) and (
            "employeename" in cols_norm or "name" in cols_norm
        ):
            score += 10  # strong signal this is the real staff sheet
        if score > best_score:
            best_score, best_name = score, name
    if best_score > 0:
        return best_name
    return xls.sheet_names[0] if xls.sheet_names else None


def _first(row, colmap: dict, *keys):
    """Row (pandas Series) se pehla non-empty matching column value nikalta hai.
    Matches column names loosely via colmap, so header wording/casing/spacing
    differences (e.g. 'OFF1' vs 'Off Day 1', 'Pickup point' vs 'PickupPoint')
    don't need to be listed as exact strings."""
    for k in keys:
        col = colmap.get(_norm(k))
        if col is None:
            continue
        v = row.get(col)
        if v is not None and str(v).strip() and str(v).strip().lower() != "nan":
            return str(v).strip()
    return ""


# ----------------------------------------------------------------------
# 1. STAFF DATA LOADER
#    Field names match exactly what the kiosk JS below expects:
#    id, name, shift, off1, off2, dept, manager, company, doj, phone,
#    birthday, hours, shift_time, pickup, email, country, job_title,
#    tenure_end, aliases (list)
# ----------------------------------------------------------------------
def load_staff_data() -> list:
    if not os.path.exists(DATA_FILE):
        return []
    try:
        if DATA_FILE.endswith(".csv"):
            df = pd.read_csv(DATA_FILE, dtype=str).fillna("")
        else:
            sheet = _pick_best_sheet(DATA_FILE)
            df = pd.read_excel(
                DATA_FILE, sheet_name=sheet, dtype=str, engine="openpyxl"
            ).fillna("")

        colmap = _colmap(df)

        records = []
        for _, row in df.iterrows():
            badge = _first(row, colmap, "EmployeeID", "Badge ID", "BadgeID")
            if not badge:
                continue

            off1 = _first(row, colmap, "OffDay1", "WeekOff1", "Off Day 1", "OFF1", "Off1")
            off2 = _first(row, colmap, "OffDay2", "WeekOff2", "Off Day 2", "OFF2", "Off2")
            if not off1 and not off2:
                combined = _first(row, colmap, "NextOffDay", "WeekOff", "Week Off")
                if combined:
                    parts = [
                        p.strip()
                        for p in combined.replace("&", ",").replace(" and ", ",").split(",")
                        if p.strip()
                    ]
                    off1 = parts[0] if len(parts) > 0 else combined
                    off2 = parts[1] if len(parts) > 1 else ""

            aliases_raw = _first(row, colmap, "Aliases", "Alias")
            aliases = [a.strip() for a in aliases_raw.split(",") if a.strip()]

            records.append(
                {
                    "id": badge,
                    "name": _first(row, colmap, "Name", "Employee Name", "Full Name"),
                    "shift": _first(row, colmap, "Shift", "Status"),
                    "off1": off1,
                    "off2": off2,
                    "dept": _first(row, colmap, "Department", "Dept"),
                    "manager": _first(row, colmap, "Manager", "Line Manager", "Supervisor"),
                    "company": _first(row, colmap, "Company", "Agency", "3P"),
                    "job_title": _first(row, colmap, "Job Title", "JobTitle", "Designation", "Position"),
                    "doj": _first(row, colmap, "DOJ", "JoiningDate", "Date of Joining"),
                    "phone": _first(row, colmap, "Phone", "PhoneNumber", "Phone Number"),
                    "birthday": _first(row, colmap, "Birthday", "BirthdayMonth", "Birthday Month"),
                    "hours": _first(row, colmap, "WorkingHours", "Hours", "Working Hours"),
                    "shift_time": _first(row, colmap, "ShiftTiming", "ShiftTime", "Shift Timing"),
                    "pickup": _first(row, colmap, "Pickup", "PickupPoint", "Pickup Point"),
                    "email": _first(row, colmap, "Email", "Email Address"),
                    "country": _first(row, colmap, "Country", "HomeCountry", "Home Country", "Home county"),
                    "tenure_end": _first(row, colmap, "TenureEnd", "ContractEnd", "Tenure End", "Tenure end"),
                    "aliases": aliases,
                }
            )
        return records
    except Exception as e:
        st.sidebar.error(f"Data load error: {e}")
        return []


# ----------------------------------------------------------------------
# 1b. BACKGROUND THEME VIDEOS
#     Streamlit's components.html() renders the kiosk inside a sandboxed
#     iframe, so a plain relative filename like "banner.mp4" does NOT
#     resolve to the file sitting next to app.py - that was the reason
#     the banner video wasn't showing at all. We read each theme file
#     that exists next to app.py and inline it as a base64 data URI
#     instead, which always works regardless of how Streamlit serves
#     the app.
#
#     To add a theme: just drop a file with one of the names below next
#     to app.py (banner.mp4 is the default/first theme). A small dot
#     appears in the kiosk's top-right for every theme that loads
#     successfully, letting staff switch between them live.
# ----------------------------------------------------------------------
THEME_FILENAMES = ["banner.mp4", "banner2.mp4", "banner3.mp4"]
MAX_THEME_VIDEO_MB = 20  # safety cap so one huge video doesn't bloat the page


def _video_to_data_uri(path: str) -> str:
    try:
        size_mb = os.path.getsize(path) / (1024 * 1024)
        if size_mb > MAX_THEME_VIDEO_MB:
            st.sidebar.warning(
                f"{os.path.basename(path)} is {size_mb:.1f}MB - skipped "
                f"(over the {MAX_THEME_VIDEO_MB}MB embed limit)."
            )
            return ""
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        return f"data:video/mp4;base64,{encoded}"
    except Exception as e:
        st.sidebar.error(f"Video load error ({os.path.basename(path)}): {e}")
        return ""


def load_themes() -> list:
    themes = []
    for fname in THEME_FILENAMES:
        fpath = os.path.join(APP_DIR, fname)
        if os.path.exists(fpath):
            data_uri = _video_to_data_uri(fpath)
            if data_uri:
                themes.append({"name": fname, "src": data_uri})
    return themes


# ----------------------------------------------------------------------
# 2. ADMIN SIDEBAR (password-protected data upload)
# ----------------------------------------------------------------------
with st.sidebar:
    st.markdown("### PXT Admin")
    pwd = st.text_input("Password", type="password", placeholder="Admin password")

    if pwd:
        if pwd == ADMIN_PASSWORD:
            st.success("Access Granted")

            uploaded = st.file_uploader("Upload data.csv or data.xlsx", type=["csv", "xlsx"])
            if uploaded:
                try:
                    target_name = "data.csv" if uploaded.name.endswith(".csv") else "data.xlsx"
                    save_path = os.path.join(APP_DIR, target_name)
                    with open(save_path, "wb") as f:
                        f.write(uploaded.getbuffer())
                    st.success("File uploaded successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

            staff_preview = load_staff_data()
            st.caption(f"{len(staff_preview)} staff records loaded.")
            if DATA_FILE.endswith(".xlsx"):
                st.caption(f"Reading sheet: '{_pick_best_sheet(DATA_FILE)}'")
            if staff_preview:
                st.dataframe(pd.DataFrame(staff_preview), use_container_width=True)

            theme_preview = load_themes()
            if theme_preview:
                st.caption(
                    f"{len(theme_preview)} background theme video(s) loaded: "
                    + ", ".join(t["name"] for t in theme_preview)
                )
            else:
                st.caption("No background theme video found - add banner.mp4 next to app.py.")
        else:
            st.error("Incorrect password")

# ----------------------------------------------------------------------
# 3. HIDE STREAMLIT CHROME & UI CLEANUP
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
    #MainMenu, footer, header {display:none !important;}
    [data-testid="stToolbar"], [data-testid="stStatusWidget"], [data-testid="stDecoration"] {display:none !important;}
    div.block-container {padding: 0 !important; margin: 0 !important; max-width: 100% !important;}
    html, body, [data-testid="stAppViewContainer"] {background: #090d16; overflow: hidden;}
    /* Force the kiosk's iframe (and the banner video inside it) to fill
       the entire browser viewport on any screen/tablet size, instead of
       being boxed into the fixed pixel height Streamlit gives components.html.
       This is what actually made the banner look "not fit on screen". */
    iframe {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        border: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# 4. SINGLE-FILE KIOSK HTML/JS/VOICE COMPONENT
#    The full kiosk frontend is embedded below as a raw string (not an
#    f-string) to avoid having to escape the JS's own curly braces.
#    __STAFF__ and __THEMES__ are simple text placeholders swapped out
#    with .replace() right before rendering.
# ----------------------------------------------------------------------
staff_data = load_staff_data()
staff_json = json.dumps(staff_data, ensure_ascii=False)

themes_data = load_themes()
themes_json = json.dumps(themes_data, ensure_ascii=False)

KIOSK_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"><title>PXT Hub</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
html,body{width:100%;height:100%;background:#05070c;font-family:'Segoe UI',Arial,sans-serif;overflow:hidden;color:#eaf6ff;}
.kiosk{position:relative;width:100vw;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;overflow:hidden;padding-bottom:12px;}
.bg-video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center center;z-index:0;opacity:.85;}
.bg-grad{position:absolute;inset:0;z-index:0;
    background:radial-gradient(circle at 20% 30%,rgba(0,180,255,.15),transparent 45%),
               radial-gradient(circle at 80% 70%,rgba(0,255,200,.12),transparent 45%),
               linear-gradient(120deg,#05070c,#0a0f1a 40%,#05070c);
    background-size:200% 200%;animation:bgshift 18s ease-in-out infinite;}
@keyframes bgshift{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.grid-ov{position:absolute;inset:0;z-index:0;
    background-image:linear-gradient(rgba(0,220,255,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(0,220,255,.05) 1px,transparent 1px);
    background-size:42px 42px;mask-image:radial-gradient(circle at 50% 40%,black 10%,transparent 75%);}
.scrim{position:absolute;inset:0;z-index:1;background:radial-gradient(circle at 50% 45%,rgba(5,7,12,.15),rgba(5,7,12,.85) 75%);}

.top-bar{position:fixed;top:0;left:0;right:0;z-index:5;display:flex;align-items:center;justify-content:space-between;padding:12px 20px;background:transparent;}
.mic-ind{display:flex;align-items:center;gap:6px;}
.mic-dot{width:9px;height:9px;border-radius:50%;background:#ff5b5b;box-shadow:0 0 8px rgba(255,80,80,.8);transition:all .3s;}
.mic-dot.on{background:#46ffb0;box-shadow:0 0 10px rgba(70,255,176,.9);}
.mic-label{font-size:10px;color:#7fd0ef;letter-spacing:1px;text-transform:uppercase;}
.debug{color:#5fa8c4;font-size:10.5px;background:rgba(10,16,26,.5);padding:4px 12px;border-radius:999px;border:1px solid rgba(80,200,255,.15);max-width:50vw;text-align:center;opacity:.7;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}

.pulse-ring{display:none;}

/* Top-left greeting, matching the reference layout (no user name shown here). */
.top-greet{position:fixed;top:52px;left:20px;z-index:5;text-align:left;}
.top-greet .g1{font-size:16px;font-weight:600;color:#eaf6ff;}
.top-greet .g2{font-size:12px;color:rgba(234,246,255,.55);margin-top:3px;}
.top-greet .g3{font-size:11px;color:rgba(127,208,239,.7);margin-top:10px;background:rgba(10,16,26,.55);border:1px solid rgba(80,200,255,.2);padding:5px 12px;border-radius:999px;display:inline-block;}

/* Headline block above the voice widget */
.headline{position:relative;z-index:2;text-align:center;margin-bottom:16px;padding:0 20px;}
.headline h1{font-size:24px;font-weight:700;color:#eaf6ff;letter-spacing:.2px;}
.headline h1 .hl{color:#8b7cff;}
.headline p{font-size:13px;color:rgba(143,184,207,.8);margin-top:6px;}

/* Small mic + waveform widget (replaces the old big pulse-ring icon) */
.voice-widget{position:relative;z-index:2;display:flex;align-items:center;justify-content:center;gap:14px;background:rgba(15,22,34,.55);border:1px solid rgba(90,210,255,.18);border-radius:22px;padding:18px 26px;backdrop-filter:blur(10px);margin-bottom:8px;}
.wave-bars{display:flex;align-items:center;gap:3px;height:34px;min-width:150px;}
.wave-bars .bar{width:3px;border-radius:2px;background:linear-gradient(180deg,#3ecbff,#7c8fff);height:6px;transition:height .15s ease;}
.wave-bars.right .bar{background:linear-gradient(180deg,#b06bff,#ff6bd8);}
.wave-bars.active .bar{animation:wavebar 900ms ease-in-out infinite;}
@keyframes wavebar{0%,100%{height:6px;}50%{height:30px;}}
.wave-bars .wave-label{display:none;font-size:12px;font-weight:500;color:#9fd8ef;white-space:nowrap;}
.wave-bars.right .wave-label{color:#e2b6ff;}
.wave-bars.text-mode .bar{display:none;}
.wave-bars.text-mode .wave-label{display:block;}
.wave-bars.left.text-mode{justify-content:flex-end;}
.wave-bars.right.text-mode{justify-content:flex-start;}

.mic-small{position:relative;width:54px;height:54px;border-radius:50%;border:2px solid rgba(90,150,255,.6);display:flex;align-items:center;justify-content:center;flex-shrink:0;background:rgba(20,40,80,.4);box-shadow:0 0 16px rgba(70,140,255,.25);transition:all .25s;}
.mic-small.active{animation:micGlow 1.6s ease-in-out infinite;border-color:rgba(120,190,255,.9);}
@keyframes micGlow{0%,100%{box-shadow:0 0 18px rgba(70,180,255,.5);}50%{box-shadow:0 0 34px rgba(70,210,255,.95);}}
.mic-small .blink-dot{position:absolute;top:1px;right:1px;width:11px;height:11px;border-radius:50%;background:#46ffb0;box-shadow:0 0 8px rgba(70,255,176,.9);opacity:0;transition:opacity .2s;border:2px solid #05070c;}
.mic-small.active .blink-dot{opacity:1;animation:blinkDot 1s ease-in-out infinite;}
@keyframes blinkDot{0%,100%{opacity:1;}50%{opacity:.2;}}
.mic-small svg{width:20px;height:20px;}

.status-display{position:relative;z-index:2;text-align:center;max-width:500px;padding:0 20px;}
.status-main{font-size:13px;font-weight:400;color:rgba(234,246,255,.6);min-height:18px;transition:all .3s;letter-spacing:.3px;line-height:1.5;}
.status-sub{font-size:11px;color:rgba(127,208,239,.5);min-height:14px;transition:all .3s;margin-top:4px;}

.login-badge{position:relative;z-index:2;text-align:center;font-size:12px;color:rgba(159,216,239,.85);letter-spacing:.3px;margin-top:4px;min-height:16px;}
.c-pres{color:#4dffb0;} .c-abs{color:#ff6767;} .c-oth{color:#ffd166;}
@keyframes pop{from{opacity:0;transform:translateY(10px) scale(.96)}to{opacity:1;transform:translateY(0) scale(1)}}

/* Start overlay */
.start-overlay{position:fixed;inset:0;z-index:100;background:rgba(5,7,12,.94);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;backdrop-filter:blur(6px);}
.start-overlay h2{color:#eaf6ff;font-size:24px;font-weight:700;}
.start-overlay p{color:#8fb8cf;font-size:14px;max-width:400px;text-align:center;line-height:1.6;}
.sel-wrap{display:flex;flex-direction:column;align-items:center;gap:6px;}
.sel-wrap label{color:#7fd0ef;font-size:11px;letter-spacing:1px;text-transform:uppercase;}
.sel{padding:9px 16px;border-radius:12px;border:1px solid rgba(0,190,255,.3);background:rgba(10,16,26,.8);color:#dff5ff;font-size:13px;min-width:280px;outline:none;}
.sel option{background:#0a0d14;color:#dff5ff;}
.start-btn{padding:14px 36px;border-radius:999px;border:1px solid rgba(0,190,255,.4);background:rgba(0,150,255,.15);color:#dff5ff;font-size:16px;font-weight:600;cursor:pointer;transition:all .2s;letter-spacing:.5px;margin-top:6px;}
.start-btn:hover{background:rgba(0,150,255,.3);box-shadow:0 0 20px rgba(0,190,255,.3);}
.start-btn:disabled{opacity:.4;cursor:not-allowed;}
.mic-test{display:flex;align-items:center;gap:10px;margin:4px 0;}
.mic-test-bar{width:160px;height:8px;background:rgba(255,255,255,.08);border-radius:6px;overflow:hidden;}
.mic-test-fill{height:100%;width:0%;background:#46ffb0;border-radius:6px;transition:width .1s;}
.mic-test-label{font-size:10px;color:#8fb8cf;}
.voice-preview{padding:8px 18px;border-radius:999px;border:1px solid rgba(0,190,255,.25);background:rgba(0,150,255,.08);color:#9fd8ef;font-size:12px;cursor:pointer;transition:all .2s;margin-top:2px;}
.voice-preview:hover{background:rgba(0,150,255,.2);}
.theme-dots{display:flex;gap:8px;align-items:center;flex-shrink:0;}
.theme-dot{width:12px;height:12px;border-radius:50%;border:2px solid rgba(0,190,255,.4);background:rgba(255,255,255,.1);cursor:pointer;transition:all .25s;opacity:.55;flex-shrink:0;}
.theme-dot:hover{opacity:1;box-shadow:0 0 10px rgba(0,190,255,.5);transform:scale(1.2);}
.theme-dot.active{opacity:1;background:linear-gradient(135deg,#0af,#0fa);box-shadow:0 0 10px rgba(0,190,255,.6);}
</style>
</head>
<body>
<div class="start-overlay" id="startOverlay">
    <h2>🎙️ PXT Hub</h2>
    <p>Set up your microphone and voice, then start.</p>

    <div class="sel-wrap">
        <label>🎙️ Microphone</label>
        <select class="sel" id="micSelect"><option value="">Loading...</option></select>
    </div>
    <div class="mic-test">
        <div class="mic-test-bar"><div class="mic-test-fill" id="testFill"></div></div>
        <div class="mic-test-label" id="testLabel">Select mic</div>
    </div>

    <div class="sel-wrap" style="margin-top:8px;">
        <label>🗣️ Voice</label>
        <select class="sel" id="voiceSelect"><option value="">Loading voices...</option></select>
    </div>
    <button class="voice-preview" id="voicePreview">▶ Preview voice</button>

    <button class="start-btn" id="startBtn" disabled>🎙️ Start</button>
</div>

<div class="kiosk" id="kiosk" style="display:none;">
    <video class="bg-video" id="bgVideo" autoplay loop playsinline style="display:none;"></video>
    <div class="bg-grad" id="bgGrad"></div><div class="grid-ov"></div><div class="scrim"></div>
    <div class="top-bar">
        <div class="mic-ind"><div class="mic-dot" id="micDot"></div><div class="mic-label" id="micLabel">MIC OFF</div></div>
        <div class="debug" id="debug">&nbsp;</div>
        <div class="theme-dots" id="themeDots"></div>
    </div>
    <div class="top-greet" id="topGreet">
        <div class="g1" id="greetLine1">Good Afternoon 👋</div>
        <div class="g2">How can I help you today?</div>
        <div class="g3" id="p1">PXT Hub</div>
    </div>
    <div class="headline">
        <h1>I'm Your PXT <span class="hl">AI</span> Assistant</h1>
        <p>You can ask me anything or give a command.</p>
    </div>
    <div class="voice-widget" id="voiceWidget">
        <div class="wave-bars left" id="waveLeft"><div class="wave-label" id="waveLeftLabel"></div></div>
        <div class="mic-small" id="micSmall">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Z" stroke="#7fd0ef" stroke-width="1.6"/>
                <path d="M19 11a7 7 0 0 1-14 0M12 18v3" stroke="#7fd0ef" stroke-width="1.6" stroke-linecap="round"/>
            </svg>
            <div class="blink-dot"></div>
        </div>
        <div class="wave-bars right" id="waveRight"><div class="wave-label" id="waveRightLabel"></div></div>
    </div>
    <div class="pulse-ring" id="pulseRing"><div class="icon">🎙️</div></div>
    <!-- Badge ID input for manual entry (RFID later) -->
    <div id="badgeWrap" style="position:relative;z-index:2;display:none;margin-bottom:16px;">
        <div style="display:flex;align-items:center;gap:8px;">
            <input type="text" id="badgeInput" placeholder="Enter Badge ID" autocomplete="off" inputmode="numeric" pattern="[0-9]*"
                style="padding:10px 18px;border-radius:12px;border:1px solid rgba(0,190,255,.4);background:rgba(10,16,26,.8);color:#dff5ff;font-size:18px;width:220px;text-align:center;outline:none;letter-spacing:2px;" />
            <button id="badgeBtn" style="padding:10px 20px;border-radius:12px;border:1px solid rgba(0,190,255,.4);background:rgba(0,150,255,.2);color:#dff5ff;font-size:14px;cursor:pointer;font-weight:600;">GO</button>
        </div>
        <div style="color:rgba(127,208,239,.6);font-size:10px;margin-top:6px;text-align:center;">Or say your Badge ID number</div>
    </div>
    <div class="status-display">
        <div class="status-main" id="statusMain"></div>
        <div class="status-sub" id="statusSub"></div>
    </div>
    <div class="login-badge" id="loginBadge"></div>
</div>

<script>
(function(){
var STAFF=__STAFF__;
var THEMES=__THEMES__; // [{name, src(data-uri)}, ...] background theme videos
var $=function(id){return document.getElementById(id);};
var micDot=$('micDot'),micLabel=$('micLabel'),debug=$('debug');
var statusMain=$('statusMain'),statusSub=$('statusSub');
var pulseRing=$('pulseRing'),p1=$('p1');
var micSmall=$('micSmall'),waveLeft=$('waveLeft'),waveRight=$('waveRight');
var waveLeftLabel=$('waveLeftLabel'),waveRightLabel=$('waveRightLabel'),greetLine1=$('greetLine1');
var bgVideo=$('bgVideo'),bgGrad=$('bgGrad');
var loginBadge=$('loginBadge');
var micSelect=$('micSelect'),testFill=$('testFill'),testLabel=$('testLabel'),startBtn=$('startBtn');
var voiceSelect=$('voiceSelect'),voicePreview=$('voicePreview');

/* ===== THEME SWITCH DOTS =====
   One dot per background theme video that actually loaded. Click a dot
   to switch. If only zero/one theme is available, no dots are shown -
   nothing to switch between yet. */
var currentTheme=0;
var themeDotsWrap=$('themeDots');
function renderThemeDots(){
    if(!themeDotsWrap)return;
    themeDotsWrap.innerHTML='';
    if(!THEMES||THEMES.length<2)return;
    THEMES.forEach(function(t,i){
        var d=document.createElement('div');
        d.className='theme-dot'+(i===currentTheme?' active':'');
        d.title=t.name||('Theme '+(i+1));
        d.onclick=function(){switchTheme(i);};
        themeDotsWrap.appendChild(d);
    });
}
function switchTheme(i){
    if(!THEMES||!THEMES[i]||i===currentTheme)return;
    currentTheme=i;
    renderThemeDots();
    if(bgVideo&&THEMES[i].src){
        var vol=bgVideo.volume,mut=bgVideo.muted;
        bgVideo.src=THEMES[i].src;
        bgVideo.volume=vol;bgVideo.muted=mut;
        bgVideo.style.display='block';
        if(bgGrad)bgGrad.style.display='none';
        bgVideo.play().catch(function(){bgVideo.muted=true;bgVideo.play().catch(function(){});});
    }
}
var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
if(!SR){startBtn.style.display='none';return;}

var speaking=false,listening=false,rec=null,lastActivity=Date.now();
var restartTimeout=null,micStream=null,selectedDeviceId=null,testStream=null,testMeter=null;
var userName=null,userStaff=null,sleepTimer=null,chosenVoice=null,wakeTimeoutTimer=null;
var state='sleep'; // sleep | wake_listen | ready
var SLEEP_TIMEOUT=30000; // inactivity timeout once logged in (ready state)
var WAKE_TIMEOUT=25000;  // seconds allowed to enter a badge before going back to sleep

/* ===== VOICE ===== */
var VP=['Google UK English Female','Google US English','Microsoft Zira','Microsoft Jenny','Samantha','Karen','Microsoft David'];
function loadVoices(){
    var voices=window.speechSynthesis.getVoices();if(!voices.length)return;
    voiceSelect.innerHTML='';
    var en=voices.filter(function(v){return v.lang.startsWith('en');});
    var added={};
    VP.forEach(function(p){var v=voices.find(function(x){return x.name.indexOf(p)>=0;});
        if(v&&!added[v.name]){var o=document.createElement('option');o.value=v.name;o.textContent='⭐ '+v.name;voiceSelect.appendChild(o);added[v.name]=1;}});
    en.forEach(function(v){if(!added[v.name]){var o=document.createElement('option');o.value=v.name;o.textContent=v.name;voiceSelect.appendChild(o);added[v.name]=1;}});
    chosenVoice=null;
    for(var i=0;i<VP.length;i++){var v=voices.find(function(x){return x.name.indexOf(VP[i])>=0;});if(v){chosenVoice=v;voiceSelect.value=v.name;break;}}
    if(!chosenVoice&&en.length){chosenVoice=en[0];voiceSelect.value=en[0].name;}
}
window.speechSynthesis.onvoiceschanged=loadVoices;loadVoices();
voiceSelect.onchange=function(){var v=window.speechSynthesis.getVoices();chosenVoice=v.find(function(x){return x.name===voiceSelect.value;})||null;};
voicePreview.onclick=function(){try{window.speechSynthesis.cancel();}catch(e){}var u=new SpeechSynthesisUtterance("Hello! I am your PXT Hub assistant.");u.rate=0.95;u.pitch=1.05;if(chosenVoice)u.voice=chosenVoice;window.speechSynthesis.speak(u);};

/* ===== HELPERS ===== */
function norm(s){return(s||"").toLowerCase().trim().replace(/[^a-z0-9\s]/g,"").replace(/\s+/g," ");}
function pick(a){return a[Math.floor(Math.random()*a.length)];}
function log(m){debug.textContent=m;}

/* Build the animated waveform bars once (random heights/delays so the
   two sides don't pulse in perfect lock-step - it "weaves" like the
   reference screenshot). Only the CSS animation runs continuously;
   we just toggle the .active class on/off depending on mic state. */
function buildWaveBars(container,count){
    if(!container)return;
    for(var i=0;i<count;i++){
        var b=document.createElement('div');
        b.className='bar';
        b.style.animationDelay=(Math.random()*0.9).toFixed(2)+'s';
        b.style.animationDuration=(0.6+Math.random()*0.6).toFixed(2)+'s';
        container.appendChild(b);
    }
}
buildWaveBars(waveLeft,14);
buildWaveBars(waveRight,14);

function setMic(on){
    micDot.classList.toggle('on',on);
    micLabel.textContent=on?'LISTENING':'MIC OFF';
    pulseRing.classList.toggle('active',on);
    if(micSmall)micSmall.classList.toggle('active',on);
    if(waveLeft)waveLeft.classList.toggle('active',on);
    if(waveRight)waveRight.classList.toggle('active',on);
}
function setStatus(m,s){statusMain.textContent=m||'';statusSub.textContent=s||'';}

/* Puts short instructional text directly in place of the waveform bars
   (used only while the kiosk is asleep, waiting for the wake word) -
   e.g. "Say 'Hi PXT'" on the left, "to wake me up" on the right. */
function setWavePrompt(leftText,rightText){
    if(waveLeft){waveLeft.classList.add('text-mode');}
    if(waveRight){waveRight.classList.add('text-mode');}
    if(waveLeftLabel)waveLeftLabel.textContent=leftText||'';
    if(waveRightLabel)waveRightLabel.textContent=rightText||'';
}
function clearWavePrompt(){
    if(waveLeft)waveLeft.classList.remove('text-mode');
    if(waveRight)waveRight.classList.remove('text-mode');
}

/* Top-left greeting text (time-of-day only - no user name shown here). */
function updateGreeting(){
    if(greetLine1) greetLine1.textContent=timeGreet()+" 👋";
}
updateGreeting();
setInterval(updateGreeting,60000);
function setPill(t){p1.textContent=t;}
/* Replaces the old big employee-details card with one small line of text
   ("Badge: 12345 • Logged in") so the layout doesn't shift/grow after
   login - full details (shift, off days, etc.) are still available by
   asking, and are spoken + shown in the status caption above. */
function hideCard(){if(loginBadge)loginBadge.textContent='';}
function showCard(s){
    if(loginBadge)loginBadge.textContent='Badge: '+s.id+' • Logged in';
}

/* ===== MIC SETUP ===== */
async function loadMics(){
    try{var ts=await navigator.mediaDevices.getUserMedia({audio:true});ts.getTracks().forEach(function(t){t.stop();});
    var devs=await navigator.mediaDevices.enumerateDevices();var mics=devs.filter(function(d){return d.kind==='audioinput';});
    micSelect.innerHTML='';
    mics.forEach(function(m,i){var o=document.createElement('option');o.value=m.deviceId;o.textContent=m.label||('Mic '+(i+1));micSelect.appendChild(o);});
    if(mics.length){selectedDeviceId=mics[0].deviceId;startBtn.disabled=false;testMicDev(selectedDeviceId);}
    }catch(e){micSelect.innerHTML='<option>Denied</option>';}
}
async function testMicDev(id){
    if(testStream){testStream.getTracks().forEach(function(t){t.stop();});}if(testMeter){testMeter.stop();}
    testFill.style.width='0%';
    try{testStream=await navigator.mediaDevices.getUserMedia({audio:{deviceId:{exact:id}}});
    var ctx=new(window.AudioContext||window.webkitAudioContext)();var a=ctx.createAnalyser();a.fftSize=256;
    ctx.createMediaStreamSource(testStream).connect(a);var d=new Uint8Array(a.frequencyBinCount);var on=true;
    (function tk(){if(!on)return;a.getByteFrequencyData(d);var s=0;for(var i=0;i<d.length;i++)s+=d[i];
    var p=Math.min(100,Math.round((s/d.length)/128*100));testFill.style.width=p+'%';
    testFill.style.background=p>30?'#46ffb0':p>10?'#ffd166':'#ff5b5b';requestAnimationFrame(tk);})();
    testMeter={stop:function(){on=false;try{ctx.close();}catch(e){}}};
    }catch(e){}
}
micSelect.onchange=function(){selectedDeviceId=micSelect.value;if(selectedDeviceId)testMicDev(selectedDeviceId);};

/* ===== TTS =====
   IMPORTANT LIMITATION: this kiosk uses the browser's built-in Web Speech
   API (window.speechSynthesis) - there is no server/API integration here,
   so voice quality depends entirely on what's installed on the machine/OS
   running the kiosk. English-only build - always uses the chosen English
   voice. */
function speak(text,cb){
    speaking=true;stopListening();clearTimeout(sleepTimer);
    try{window.speechSynthesis.cancel();}catch(e){}
    setStatus(text,"");
    var u=new SpeechSynthesisUtterance(text);
    u.lang='en-US';u.rate=0.95;u.pitch=1.05;
    if(chosenVoice){u.voice=chosenVoice;}
    var done=false;function fin(){if(done)return;done=true;speaking=false;if(cb)cb();}
    u.onend=fin;u.onerror=fin;window.speechSynthesis.speak(u);
    setTimeout(fin,Math.max(text.length*100,3000)+5000);
}

/* ===== BADGE LOOKUP ===== */
function findByBadge(id){
    id=id.trim();
    for(var i=0;i<STAFF.length;i++){
        var sid=String(STAFF[i].id).trim();
        if(sid===id)return STAFF[i];
        // Partial match (last 6 digits)
        if(id.length>=6 && sid.indexOf(id)>=0)return STAFF[i];
        if(id.length>=6 && sid.slice(-6)===id.slice(-6))return STAFF[i];
    }
    return null;
}

// Badge input handler
document.addEventListener('DOMContentLoaded',function(){
    var bi=document.getElementById('badgeInput');
    var bb=document.getElementById('badgeBtn');
    if(bb) bb.onclick=function(){if(bi&&bi.value.trim().length>=3) handleBadgeEntry(bi.value.trim());};
    if(bi) bi.onkeydown=function(e){if(e.key==='Enter'&&bi.value.trim().length>=3) handleBadgeEntry(bi.value.trim());};
});
function handleBadgeEntry(val){
    var bw=document.getElementById('badgeWrap');if(bw)bw.style.display='none';
    handleLogin(val);
}


function timeGreet(){var h=new Date().getHours();return h<12?"Good morning":h<17?"Good afternoon":"Good evening";}
function timeStr(){return new Date().toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit'});}
function dateStr(){
    return new Date().toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric',year:'numeric'});
}

/* ===== WAKE WORD - ultra broad ===== */
function isWake(raw){
    var n=norm(raw);
    return n.indexOf('pxt')>=0 || n.indexOf('bxt')>=0 || n.indexOf('txt')>=0 ||
           n.indexOf('pct')>=0 || n.indexOf('pix')>=0 || n.indexOf('pkt')>=0 ||
           n.indexOf('vxt')>=0 || n.indexOf('dxt')>=0 || n.indexOf('cxt')>=0 ||
           n.indexOf('hey')>=0 || n.indexOf('hi')>=0 || n.indexOf('hello')>=0 ||
           n.indexOf('start')>=0 || n.indexOf('wake')>=0 || n.indexOf('listen')>=0;
}

/* ===== STATE MANAGEMENT ===== */
function goToSleep(){
    state='sleep';userName=null;userStaff=null;
    clearTimeout(sleepTimer);clearTimeout(wakeTimeoutTimer);
    hideCard();
    var bw=document.getElementById('badgeWrap');if(bw)bw.style.display='none';
    setStatus("","");
    setWavePrompt('Say "Hi PXT"','to wake me up');
    setPill("PXT Hub • Sleeping");
    log("Status: Sleeping");
    startListening();
}

function wakeUp(){
    state='wake_listen';
    clearTimeout(wakeTimeoutTimer);
    hideCard();
    clearWavePrompt();
    var bw=document.getElementById('badgeWrap');
    if(bw){
        bw.style.display='block';
        var bi=document.getElementById('badgeInput');
        if(bi){bi.value='';bi.focus();}
    }
    var msg="Hello! Please state or enter your Badge ID number to log in.";
    setStatus(msg,"Listening for Badge ID...");
    setPill("PXT Hub • Enter Badge ID");
    speak(msg,function(){
        startListening();
        // 20-25s wake timeout - returns to sleep if nobody enters a badge in time
        clearTimeout(wakeTimeoutTimer);
        wakeTimeoutTimer=setTimeout(function(){
            if(state==='wake_listen'){
                log("Wake timeout - returning to sleep");
                speak("No Badge ID received. Going back to sleep.",function(){goToSleep();});
            }
        },22000);
    });
}

function resetSleepTimer(){
    clearTimeout(sleepTimer);
    if(state==='ready'){
        sleepTimer=setTimeout(function(){
            speak("Session timed out. Have a great day!",function(){goToSleep();});
        },SLEEP_TIMEOUT);
    }
}

/* Extract badge numbers from spoken text ("my badge is 1024", "1 0 2 4", etc.) */
function extractBadgeFromSpeech(raw){
    var text=raw.toLowerCase().replace(/-/g,' ');
    // Word to digit mapping for spoken numbers
    var w2d={'zero':'0','one':'1','two':'2','to':'2','too':'2','three':'3','tree':'3','four':'4','for':'4','fore':'4','five':'5','six':'6','seven':'7','eight':'8','ate':'8','nine':'9'};
    var parts=text.split(/\s+/);
    var digits='';
    for(var i=0;i<parts.length;i++){
        var p=parts[i].replace(/[^a-z0-9]/g,'');
        if(/^\d+$/.test(p)){
            digits+=p;
        }else if(w2d[p]){
            digits+=w2d[p];
        }
    }
    if(digits.length>=3) return digits;
    return null;
}

/* Shared "who are you / what can you do" introduction, used both before
   login (wake_listen) and after login (ready) - anyone can ask this,
   with or without a badge. */
var IDENTITY_MSG="Hi! I'm PXT AI Assistant, your smart HR support assistant. I'm here to help employees with HR-related questions, workplace information, policies, benefits, leave, attendance, and other employee-support needs. Think of me as your virtual HR companion, available to provide quick, simple, and helpful answers whenever you need them. How can I assist you today?";

/* Quick answers during wake_listen ("who are you", "what can you do") */
function handlePreLoginQuery(raw){
    var n=norm(raw);
    if(n.indexOf("who are you")>=0 || n.indexOf("what are you")>=0 || n.indexOf("your name")>=0 || n.indexOf("what can you do")>=0 || n.indexOf("tell me about yourself")>=0){
        speak(IDENTITY_MSG, function(){startListening();});
        return true;
    }
    if(n.indexOf("help")>=0 || n.indexOf("options")>=0){
        speak("I can check your shift, off days, department, manager, and details. Please state your Badge ID number to get started.", function(){startListening();});
        return true;
    }
    return false;
}

/* Handles logging in via Badge ID ONLY. Name guessing is completely disabled. */
function handleLogin(badgeVal){
    clearTimeout(wakeTimeoutTimer);
    var bw=document.getElementById('badgeWrap');if(bw)bw.style.display='none';
    var found=findByBadge(badgeVal);
    if(!found){
        log("Badge not found: "+badgeVal);
        speak("I couldn't find Badge ID "+badgeVal+". Please try entering or saying your Badge ID again.",function(){
            if(bw)bw.style.display='block';
            startListening();
            wakeTimeoutTimer=setTimeout(function(){
                if(state==='wake_listen'){goToSleep();}
            },20000);
        });
        return;
    }

    // Success - logged in
    userStaff=found;
    userName=found.name;
    state='ready';

    log("Logged in as: "+userName+" ("+found.id+")");
    showCard(found);
    var greeting = timeGreet() + ", " + userName + "! How can I help you today?";
    setPill("Logged in: "+userName+" ("+found.id+")");
    speak(greeting,function(){
        resetSleepTimer();
        startListening();
    });
}

/* Turns a squished/concatenated string like "AbuDhabiCentralBusStation"
   into readable words ("Abu Dhabi Central Bus Station") before it's
   spoken - some data fields (pickup point especially) come in without
   spaces between words. */
function humanize(s){
    if(!s) return s;
    return s
        .replace(/([a-z])([A-Z])/g,'$1 $2')   // camelCase -> spaced
        .replace(/([A-Za-z])([0-9])/g,'$1 $2')
        .replace(/([0-9])([A-Za-z])/g,'$1 $2')
        .replace(/[_\-]+/g,' ')
        .replace(/([,;&()])/g,' $1 ')
        .replace(/\s+/g,' ')
        .trim();
}

/* True if the normalized query contains ANY of the given phrases
   (phrases can be multi-word - norm() already lowercases and strips
   punctuation, so "what's my shift?" -> "whats my shift"). */
function matchAny(n,phrases){
    for(var i=0;i<phrases.length;i++){ if(n.indexOf(phrases[i])>=0) return true; }
    return false;
}

/* Process queries once logged in. Employees rarely use the exact column
   name, so each intent below lists many everyday ways of asking for the
   same thing rather than just the field name itself. */
function handleQuery(raw){
    resetSleepTimer();
    var n=norm(raw);
    var s=userStaff||{};

    if(!n||n.length<2){
        speak("I didn't catch that. You can ask about your shift, off days, or manager.",function(){startListening();});
        return;
    }

    // Logout / Bye
    if(matchAny(n,["bye","goodbye","exit","logout","log out","done","thank","that will be all","see you"])){
        speak("Goodbye "+userName+"! Have a great day ahead.",function(){goToSleep();});
        return;
    }

    // Identity / introduction - "who are you", "what can you do for me", etc.
    // Checked early, same wording whether or not the employee is logged in.
    if(matchAny(n,["who are you","what are you","your name","what can you do","tell me about yourself"])){
        speak(IDENTITY_MSG,function(){startListening();});
        return;
    }

    // Current date / clock time - checked early and narrowly so it
    // doesn't get swallowed by the broader "shift" intent below.
    if(matchAny(n,["what time is it","current time","what is the time","whats the time","clock","what day is it","what is the date","whats the date","todays date","today date"])){
        var msg="Today is "+dateStr()+", current time is "+timeStr()+".";
        speak(msg,function(){startListening();});
        return;
    }

    // Shift / Timing / Hours / Roster
    if(matchAny(n,["shift","timing","schedule","roster","working hours","how many hours","what time do i work","what time do i start","what time i start","when do i start","when does my shift start","when do i work","am i on day shift","am i on night shift","day shift or night","start work"])){
        var msg="Your shift is "+(s.shift||"not assigned");
        if(s.shift_time) msg+=", timing is "+s.shift_time;
        if(s.hours) msg+=", "+s.hours+" hours per day";
        msg+=".";
        speak(msg,function(){startListening();});
        return;
    }

    // Off days / Weekend / Holiday / Leave
    if(matchAny(n,["off day","off days","my off","week off","weekoff","holiday","weekend","day off","days off","rest day","when am i off","when do i rest","when is my off"])){
        var msg="Your off days are "+(s.off1||"not set");
        if(s.off2) msg+=" and "+s.off2;
        msg+=".";
        speak(msg,function(){startListening();});
        return;
    }

    // Job title / Position / Designation (checked before Department,
    // since "role"/"position" usually means the employee's job, not team)
    if(matchAny(n,["job title","my title","designation","my position","what is my role","what do i do here","what is my job","what job do i have"])){
        var msg=s.job_title?"Your job title is "+s.job_title+".":"Your job title is not listed.";
        speak(msg,function(){startListening();});
        return;
    }

    // Department / Team
    if(matchAny(n,["department","dept","my team","which team","which department","what section"])){
        var msg="You are in the "+(s.dept||"unassigned")+" department.";
        speak(msg,function(){startListening();});
        return;
    }

    // Manager / Supervisor
    if(matchAny(n,["manager","boss","supervisor","team lead","report to","who do i report","reporting manager","line manager"])){
        var msg=s.manager?"Your manager is "+s.manager+".":"Your manager information is not listed.";
        speak(msg,function(){startListening();});
        return;
    }

    // Pickup / Transport / Bus / Accommodation
    if(matchAny(n,["pickup","pick up","bus","transport","cab","shuttle","ride","where do i get picked","where can i catch","where do we live","where do i live","which camp","my camp","accommodation","where do i stay","stay location","drop off","dropoff"])){
        var msg=s.pickup?"Your pickup point is "+humanize(s.pickup)+".":"Your pickup point is not specified.";
        speak(msg,function(){startListening();});
        return;
    }

    // Phone / Contact
    if(matchAny(n,["phone","contact number","my number","mobile","cell number","what is my number","whats my number"])){
        var msg=s.phone?"Your registered phone number is "+s.phone+".":"Your phone number is not listed.";
        speak(msg,function(){startListening();});
        return;
    }

    // Email
    if(matchAny(n,["email","mail address","my mail","e mail"])){
        var msg=s.email?"Your email is "+s.email+".":"Your email is not listed.";
        speak(msg,function(){startListening();});
        return;
    }

    // Birthday
    if(matchAny(n,["birthday","bday","born","birth month","date of birth"])){
        var msg=s.birthday?"Your birthday month is "+s.birthday+".":"Your birthday is not listed.";
        speak(msg,function(){startListening();});
        return;
    }

    // Tenure / DOJ / Joining / Contract
    if(matchAny(n,["doj","joining date","date of joining","when did i join","how long have i worked","how long have i been here","tenure","contract end","when does my contract end","visa expiry","contract expiry"])){
        var msg="";
        if(s.doj) msg+="Your date of joining is "+s.doj+". ";
        if(s.tenure_end) msg+="Your contract ends on "+s.tenure_end+".";
        if(!msg) msg="Your joining details are not listed.";
        speak(msg,function(){startListening();});
        return;
    }

    // Company / Agency / Employer
    if(matchAny(n,["company","agency","employer","who do i work for","which company","staffing agency"])){
        var msg=s.company?"You are registered under "+s.company+".":"Your company is not listed.";
        speak(msg,function(){startListening();});
        return;
    }

    // Help / Options (specific list of what to ask - identity questions
    // like "what can you do" are handled earlier by IDENTITY_MSG)
    if(matchAny(n,["help","options","menu"])){
        speak("You can ask me about your shift, off days, job title, department, manager, pickup point, phone number, email, or joining date.",function(){startListening();});
        return;
    }

    // Fields the kiosk does not track at all (e.g. T-shirt / uniform size).
    // Rather than guessing or staying silent, say plainly that the info
    // isn't available and invite another question.
    if(matchAny(n,["t shirt size","tshirt size","shirt size","uniform size","dress size","shoe size"])){
        speak("I'm sorry, I don't have that information available. Please ask me something else, like your shift, off days, or department.",function(){startListening();});
        return;
    }

    // Fallback: the query didn't match anything we track - say so
    // plainly instead of just echoing back what was heard.
    speak("I'm sorry, I don't have that information available. You can ask me about your shift, off days, department, manager, or pickup point.",function(){startListening();});
}

/* ===== MAIN SPEECH RECOGNITION LOOP =====
   NOTE: listening is gated only by `speaking` (true while the kiosk itself
   is talking, so the mic doesn't pick up its own voice). There is no
   separate "permanently stopped" flag - a previous version used one
   (shouldRun) that stopListening() set to false and nothing ever set back
   to true, which silently killed the mic forever after the very first
   thing the kiosk said. That was the root cause of the kiosk "hanging"
   after login/replies and never waking back up. */
function startListening(){
    if(speaking)return;
    if(rec){try{rec.abort();}catch(e){}}

    rec=new SR();
    rec.continuous=false;
    rec.interimResults=false;
    rec.lang='en-US';

    rec.onstart=function(){listening=true;setMic(true);log("Listening ("+state+", "+rec.lang+")...");};

    rec.onresult=function(e){
        var text=e.results[0][0].transcript;
        log("Heard: \""+text+"\"");

        if(state==='sleep'){
            if(isWake(text)){
                log("Wake word detected!");
                wakeUp();
            }else{
                // Resume listening immediately if wake word wasn't heard
                setTimeout(startListening,300);
            }
        }
        else if(state==='wake_listen'){
            // Check for quick non-login queries ("who are you", etc.)
            if(handlePreLoginQuery(text)) return;

            // Extract badge digits spoken by user
            var extractedBadge=extractBadgeFromSpeech(text);
            if(extractedBadge){
                handleLogin(extractedBadge);
            }else{
                speak("Please say or enter your numerical Badge ID to log in.",function(){
                    startListening();
                });
            }
        }
        else if(state==='ready'){
            handleQuery(text);
        }
    };

    rec.onerror=function(e){
        listening=false;setMic(false);
        if(e.error!=='no-speech'&&e.error!=='aborted') log("Mic error: "+e.error);
        if(!speaking) setTimeout(startListening,1000);
    };

    rec.onend=function(){
        listening=false;setMic(false);
        if(!speaking&&state==='sleep'){
            setTimeout(startListening,500);
        }
    };

    try{rec.start();}catch(e){log("Start error: "+e.message);}
}

function stopListening(){
    if(rec){try{rec.abort();}catch(e){}}
    listening=false;setMic(false);
}

function resumeListening(){
    startListening();
}

/* ===== START BUTTON HANDLER ===== */
startBtn.onclick=async function(){
    try{
        if(testStream){testStream.getTracks().forEach(function(t){t.stop();});}
        if(testMeter){testMeter.stop();}

        micStream=await navigator.mediaDevices.getUserMedia({
            audio:{deviceId:selectedDeviceId?{exact:selectedDeviceId}:true}
        });

        $('startOverlay').style.display='none';
        $('kiosk').style.display='flex';

        // Play background video if available
        if(THEMES&&THEMES.length>0&&THEMES[0].src){
            bgVideo.src=THEMES[0].src;
            bgVideo.style.display='block';
            if(bgGrad)bgGrad.style.display='none';
            bgVideo.play().catch(function(){
                bgVideo.muted=true;
                bgVideo.play().catch(function(){});
            });
        }
        renderThemeDots();

        log("Kiosk started. Say 'Hi PXT'");
        goToSleep();
    }catch(e){
        alert("Microphone access failed: "+e.message);
    }
};

// Initialize mic list on page load
loadMics();

})();
</script>
</body>
</html>"""

# Render full single-file app
rendered_html = KIOSK_TEMPLATE.replace("__STAFF__", staff_json).replace("__THEMES__", themes_json)
components.html(rendered_html, height=880, scrolling=False)
