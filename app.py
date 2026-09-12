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

   "what can you do" are answered directly without needing a login.

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





def _first(row, *keys):

    """Row (pandas Series) se pehla non-empty matching column value nikalta hai."""

    for k in keys:

        v = row.get(k)

        if v is not None and str(v).strip() and str(v).strip().lower() != "nan":

            return str(v).strip()

    return ""





# ----------------------------------------------------------------------

# 1. STAFF DATA LOADER

#    Field names match exactly what the kiosk JS below expects:

#    id, name, shift, off1, off2, dept, manager, company, doj, phone,

#    birthday, hours, shift_time, pickup, email, country, language,

#    tenure_end, aliases (list)

# ----------------------------------------------------------------------

def load_staff_data() -> list:

    if not os.path.exists(DATA_FILE):

        return []

    try:

        if DATA_FILE.endswith(".csv"):

            df = pd.read_csv(DATA_FILE, dtype=str).fillna("")

        else:

            df = pd.read_excel(DATA_FILE, dtype=str, engine="openpyxl").fillna("")



        records = []

        for _, row in df.iterrows():

            badge = _first(row, "EmployeeID", "Badge ID", "BadgeID")

            if not badge:

                continue



            off1 = _first(row, "OffDay1", "WeekOff1", "Off Day 1")

            off2 = _first(row, "OffDay2", "WeekOff2", "Off Day 2")

            if not off1 and not off2:

                combined = _first(row, "NextOffDay", "WeekOff", "Week Off")

                if combined:

                    parts = [

                        p.strip()

                        for p in combined.replace("&", ",").replace(" and ", ",").split(",")

                        if p.strip()

                    ]

                    off1 = parts[0] if len(parts) > 0 else combined

                    off2 = parts[1] if len(parts) > 1 else ""



            aliases_raw = _first(row, "Aliases", "Alias")

            aliases = [a.strip() for a in aliases_raw.split(",") if a.strip()]



            records.append(

                {

                    "id": badge,

                    "name": _first(row, "Name", "Employee Name"),

                    "shift": _first(row, "Shift", "Status"),

                    "off1": off1,

                    "off2": off2,

                    "dept": _first(row, "Department", "Dept"),

                    "manager": _first(row, "Manager"),

                    "company": _first(row, "Company", "Agency"),

                    "doj": _first(row, "DOJ", "JoiningDate", "Date of Joining"),

                    "phone": _first(row, "Phone", "PhoneNumber", "Phone Number"),

                    "birthday": _first(row, "Birthday", "BirthdayMonth", "Birthday Month"),

                    "hours": _first(row, "WorkingHours", "Hours"),

                    "shift_time": _first(row, "ShiftTiming", "ShiftTime", "Shift Timing"),

                    "pickup": _first(row, "Pickup", "PickupPoint", "Pickup Point"),

                    "email": _first(row, "Email"),

                    "country": _first(row, "Country", "HomeCountry", "Home Country"),

                    "language": _first(row, "Language"),

                    "tenure_end": _first(row, "TenureEnd", "ContractEnd", "Tenure End"),

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

.kiosk{position:relative;width:100vw;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;overflow:hidden;}

.bg-video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center top;z-index:0;opacity:.85;}

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



.brand{position:relative;z-index:2;color:#e8f6ff;letter-spacing:8px;font-size:20px;font-weight:700;opacity:.8;text-transform:uppercase;margin-bottom:16px;}

.pulse-ring{position:relative;z-index:2;width:110px;height:110px;border-radius:50%;border:2px solid rgba(0,190,255,.25);display:flex;align-items:center;justify-content:center;margin-bottom:24px;}

.pulse-ring.active{animation:pulse 2s ease-in-out infinite;}

@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(0,190,255,.3)}50%{box-shadow:0 0 0 22px rgba(0,190,255,0)}}

.pulse-ring .icon{font-size:42px;}



.status-display{position:relative;z-index:2;text-align:center;max-width:500px;padding:0 20px;}

.status-main{font-size:13px;font-weight:400;color:rgba(234,246,255,.6);min-height:18px;transition:all .3s;letter-spacing:.3px;line-height:1.5;}

.status-sub{font-size:11px;color:rgba(127,208,239,.5);min-height:14px;transition:all .3s;margin-top:4px;}



.rcard{position:relative;z-index:2;background:rgba(15,22,34,.75);border:1px solid rgba(90,210,255,.25);border-radius:20px;padding:24px 32px;backdrop-filter:blur(14px);text-align:center;box-shadow:0 0 30px rgba(0,150,255,.1);margin-top:18px;animation:pop .4s ease;display:none;}

.rcard.show{display:block;}

.rcard .rn{font-size:20px;font-weight:700;margin-bottom:3px;}

.rcard .ri{font-size:11px;letter-spacing:2px;color:#7fd8ff;opacity:.7;margin-bottom:14px;text-transform:uppercase;}

.rcard .rg{display:flex;justify-content:space-around;gap:14px;flex-wrap:wrap;}

.rcard .rg .ri-item .lbl{font-size:9px;letter-spacing:1.5px;color:#8fb8cf;text-transform:uppercase;margin-bottom:3px;}

.rcard .rg .ri-item .val{font-size:16px;font-weight:600;}

.c-pres{color:#4dffb0;} .c-abs{color:#ff6767;} .c-oth{color:#ffd166;}

@keyframes pop{from{opacity:0;transform:translateY(10px) scale(.96)}to{opacity:1;transform:translateY(0) scale(1)}}



.pill{position:fixed;bottom:26px;left:50%;transform:translateX(-50%);z-index:4;padding:8px 22px;border-radius:999px;background:rgba(10,16,26,.6);border:1px solid rgba(80,200,255,.2);backdrop-filter:blur(10px);text-align:center;max-width:90vw;}

.pill .p1{color:rgba(223,245,255,.7);font-size:11px;font-weight:500;letter-spacing:.4px;}



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

    <h2>&#127897;&#65039; PXT Hub</h2>

    <p>Set up your microphone and voice, then start.</p>



    <div class="sel-wrap">

        <label>&#127908; Microphone</label>

        <select class="sel" id="micSelect"><option value="">Loading...</option></select>

    </div>

    <div class="mic-test">

        <div class="mic-test-bar"><div class="mic-test-fill" id="testFill"></div></div>

        <div class="mic-test-label" id="testLabel">Select mic</div>

    </div>



    <div class="sel-wrap" style="margin-top:8px;">

        <label>&#128483;&#65039; Voice</label>

        <select class="sel" id="voiceSelect"><option value="">Loading voices...</option></select>

    </div>

    <button class="voice-preview" id="voicePreview">&#9654; Preview voice</button>



    <button class="start-btn" id="startBtn" disabled>&#127908; Start</button>

</div>



<div class="kiosk" id="kiosk" style="display:none;">

    <video class="bg-video" id="bgVideo" autoplay loop playsinline style="display:none;"></video>

    <div class="bg-grad" id="bgGrad"></div><div class="grid-ov"></div><div class="scrim"></div>

    <div class="top-bar">

        <div class="mic-ind"><div class="mic-dot" id="micDot"></div><div class="mic-label" id="micLabel">MIC OFF</div></div>

        <div class="debug" id="debug">&nbsp;</div>

        <div class="theme-dots" id="themeDots"></div>

    </div>

    <div class="brand">PXT&nbsp;HUB</div>

    <div class="pulse-ring" id="pulseRing"><div class="icon">&#127897;&#65039;</div></div>

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

    <div class="rcard" id="rcard">

        <div class="rn" id="rn"></div><div class="ri" id="ri"></div>

        <div class="rg">

            <div class="ri-item"><div class="lbl" id="rl1">Shift</div><div class="val" id="rv1"></div></div>

            <div class="ri-item"><div class="lbl" id="rl2">Off Days</div><div class="val" id="rv2"></div></div>

            <div class="ri-item"><div class="lbl" id="rl3">Department</div><div class="val" id="rv3"></div></div>

        </div>

    </div>

    <div class="pill"><div class="p1" id="p1">PXT Hub</div></div>

</div>



<script>

(function(){

var STAFF=__STAFF__;

var THEMES=__THEMES__; // [{name, src(data-uri)}, ...] background theme videos

var $=function(id){return document.getElementById(id);};

var micDot=$('micDot'),micLabel=$('micLabel'),debug=$('debug');

var statusMain=$('statusMain'),statusSub=$('statusSub');

var pulseRing=$('pulseRing'),p1=$('p1');

var bgVideo=$('bgVideo'),bgGrad=$('bgGrad');

var rcard=$('rcard'),rn=$('rn'),ri=$('ri'),rv1=$('rv1'),rv2=$('rv2'),rv3=$('rv3'),rl1=$('rl1'),rl2=$('rl2'),rl3=$('rl3');

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



var speaking=false,listening=false,rec=null,shouldRun=true,lastActivity=Date.now();

var restartTimeout=null,micStream=null,selectedDeviceId=null,testStream=null,testMeter=null;

var userName=null,userStaff=null,sleepTimer=null,chosenVoice=null,wakeTimeoutTimer=null;

var state='sleep'; // sleep | wake_listen | ready

var SLEEP_TIMEOUT=30000; // inactivity timeout once logged in (ready state)

var WAKE_TIMEOUT=25000;  // seconds allowed to enter a badge before going back to sleep

var userLang='en'; // current session language: 'en' or native code

var userNativeName=''; // e.g. 'Malayalam', 'Hindi'



/* ===== LANGUAGE SUPPORT REMOVED =====

   This kiosk now runs English-only. extractNativeLang() is kept as a

   no-op (always returns null) so downstream code (handleLogin's

   nativeLang check, etc.) continues to work unchanged and always takes

   the English path, without touching that logic. */

function extractNativeLang(langStr){

    return null;

}



/* ===== TRANSLATIONS REMOVED =====

   English-only build: tr() is kept as a no-op (always null) so every

   call site like  tr('your_shift') ? tr('your_shift') : 'your shift is'

   automatically falls through to its English default text, unchanged. */

function tr(key){

    return null;

}



function trGreet(){

    var h=new Date().getHours();

    var key=h<12?'greet_morning':h<17?'greet_afternoon':'greet_evening';

    return tr(key)||timeGreet();

}



/* ===== VOICE ===== */

var VP=['Google UK English Female','Google US English','Microsoft Zira','Microsoft Jenny','Samantha','Karen','Microsoft David'];

function loadVoices(){

    var voices=window.speechSynthesis.getVoices();if(!voices.length)return;

    voiceSelect.innerHTML='';

    var en=voices.filter(function(v){return v.lang.startsWith('en');});

    var added={};

    VP.forEach(function(p){var v=voices.find(function(x){return x.name.indexOf(p)>=0;});

        if(v&&!added[v.name]){var o=document.createElement('option');o.value=v.name;o.textContent='\u2b50 '+v.name;voiceSelect.appendChild(o);added[v.name]=1;}});

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

function setMic(on){micDot.classList.toggle('on',on);micLabel.textContent=on?'LISTENING':'MIC OFF';pulseRing.classList.toggle('active',on);}

function setStatus(m,s){statusMain.textContent=m||'';statusSub.textContent=s||'';}

function setPill(t){p1.textContent=t;}

function hideCard(){rcard.classList.remove('show');}

function showCard(s,cardInfo){

    rn.textContent=s.name;ri.textContent='Badge: '+s.id;

    if(cardInfo){rl1.textContent=cardInfo[0][0];rv1.textContent=cardInfo[0][1];rv1.className='val c-pres';rl2.textContent=cardInfo[1][0];rv2.textContent=cardInfo[1][1];rl3.textContent=cardInfo[2][0];rv3.textContent=cardInfo[2][1];}

    else{rl1.textContent='Shift';rv1.textContent=s.shift||'\u2014';rv1.className='val c-pres';rl2.textContent='Off Days';rv2.textContent=(s.off1||'')+' & '+(s.off2||'');rl3.textContent='Department';rv3.textContent=s.dept||'\u2014';}

    rcard.classList.add('show');

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

   so voice quality and which languages even have a voice at all depend

   entirely on what's installed on the machine/OS running the kiosk.

   A true "high-quality neural TTS with correct regional phonemes" (Azure

   Speech, Google Cloud TTS, ElevenLabs, etc.) would need a backend call

   with an API key and audio playback - that's a real architecture change,

   not a prompt/config tweak, and isn't something this static HTML file

   can add on its own. What IS fixed here: more robust matching so we

   actually find and use a native voice when the OS has one installed,

   instead of silently falling back to a mismatched/default voice. */

function normTag(s){return (s||'').toLowerCase().replace('_','-');}

function speak(text,cb,forceLang){

    speaking=true;stopListening();clearTimeout(sleepTimer);

    try{window.speechSynthesis.cancel();}catch(e){}

    setStatus(text,"");

    var u=new SpeechSynthesisUtterance(text);

    var lang=forceLang||(userLang==='en'?'en-US':userLang);

    u.lang=lang;u.rate=0.95;u.pitch=1.05;

    // Use chosen voice for English, auto-select for native

    if(lang==='en-US'&&chosenVoice){u.voice=chosenVoice;}

    else if(lang!=='en-US'){

        var voices=window.speechSynthesis.getVoices();

        var target=normTag(lang),base=target.split('-')[0];

        // exact tag match first, then base-language match (case/underscore tolerant)

        var nv=voices.find(function(v){return normTag(v.lang)===target;})

            ||voices.find(function(v){return normTag(v.lang).indexOf(base+'-')===0||normTag(v.lang)===base;});

        if(nv){u.voice=nv;}

        else{log('No native voice installed for '+lang+' - using device default');}

    }

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

// Date/day/month names now follow the active session language instead of

// always rendering in English (previously hardcoded to 'en-US' regardless

// of userLang - a real source of the "replies back in English" complaint).

function activeLocale(){

    if(userLang==='en'||userLang==='en-US') return 'en-US';

    // Base language subtag works for Intl even without a country match

    try{ new Intl.DateTimeFormat(userLang); return userLang; }catch(e){ return 'en-US'; }

}

function dateStr(){

    try{

        return new Date().toLocaleDateString(activeLocale(),{weekday:'long',month:'long',day:'numeric',year:'numeric'});

    }catch(e){

        return new Date().toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric',year:'numeric'});

    }

}



/* ===== WAKE WORD - ultra broad ===== */

function isWakeWord(text){

    var t=norm(text);

    // Must have a greeting

    if(!/\b(hi|hey| 

