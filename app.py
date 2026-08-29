"""
PXT Hub - AI Voice Kiosk (v2)
==============================
Full-screen voice kiosk with conversational AI.
Handles greetings, casual chat, time, jokes, AND staff lookups.
Always listening — no wake word needed.
"""

import json
import os

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------
CSV_PATH = "staff_data.csv"
ADMIN_PASSWORD = "pxt123"
REQUIRED_COLUMNS = ["EmployeeID", "Name", "Status", "RemainingLeaves", "NextOffDay"]

st.set_page_config(
    page_title="PXT Hub",
    page_icon="\U0001f399\ufe0f",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# --------------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------------
def load_staff_data() -> pd.DataFrame:
    if os.path.exists(CSV_PATH):
        try:
            df = pd.read_csv(CSV_PATH, dtype=str).fillna("")
            missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
            if missing:
                st.error(
                    f"staff_data.csv is missing column(s): {', '.join(missing)}. "
                    f"Required: {', '.join(REQUIRED_COLUMNS)}"
                )
                return pd.DataFrame(columns=REQUIRED_COLUMNS)
            return df
        except Exception as exc:
            st.error(f"Could not read staff_data.csv: {exc}")
            return pd.DataFrame(columns=REQUIRED_COLUMNS)
    return pd.DataFrame(columns=REQUIRED_COLUMNS)


def df_to_json_records(df: pd.DataFrame) -> str:
    records = df.to_dict(orient="records")
    cleaned = [
        {
            "id": str(r.get("EmployeeID", "")).strip(),
            "name": str(r.get("Name", "")).strip(),
            "status": str(r.get("Status", "")).strip(),
            "leaves": str(r.get("RemainingLeaves", "")).strip(),
            "nextoff": str(r.get("NextOffDay", "")).strip(),
            "aliases": [
                a.strip()
                for a in str(r.get("Aliases", "")).split("|")
                if a.strip()
            ],
        }
        for r in records
    ]
    return json.dumps(cleaned, ensure_ascii=False)


# --------------------------------------------------------------------------
# GLOBAL CSS
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
        #MainMenu, footer, header {visibility: hidden !important; display: none !important;}
        [data-testid="stToolbar"],
        [data-testid="stStatusWidget"],
        [data-testid="stDecoration"],
        .viewerBadge_container,
        .stActionButton,
        #manage-app-button,
        div[data-testid="manage-app-button"],
        [data-testid="stConnectionStatus"] {display:none !important;}
        div.block-container {padding:0!important; margin:0!important; max-width:100%!important;}
        html, body, [data-testid="stAppViewContainer"] {
            background: #05070c;
            overflow: hidden;
        }
        [data-testid="stSidebar"] {background: #0a0d14;}
        iframe {
            position: fixed !important;
            top: 0; left: 0;
            width: 100vw !important;
            height: 100vh !important;
            border: none !important;
            z-index: 1;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# ADMIN PANEL
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### \U0001f512 PXT Admin")
    pwd = st.text_input(
        "Admin password",
        type="password",
        label_visibility="collapsed",
        placeholder="Admin password",
    )
    if pwd == ADMIN_PASSWORD:
        st.success("Access granted")
        st.caption("Upload a replacement staff database (.csv)")
        uploaded = st.file_uploader(
            "Upload staff_data.csv", type=["csv"], label_visibility="collapsed"
        )
        if uploaded is not None:
            try:
                new_df = pd.read_csv(uploaded, dtype=str).fillna("")
                missing = [c for c in REQUIRED_COLUMNS if c not in new_df.columns]
                if missing:
                    st.error(f"Missing column(s): {', '.join(missing)}")
                else:
                    new_df.to_csv(CSV_PATH, index=False)
                    st.success("Database updated. Reloading...")
                    st.rerun()
            except Exception as exc:
                st.error(f"Failed to process file: {exc}")
        st.divider()
        st.caption("Current records")
        st.dataframe(load_staff_data(), use_container_width=True, height=300)
    elif pwd:
        st.error("Incorrect password")

# --------------------------------------------------------------------------
# LOAD DATA & BUILD KIOSK
# --------------------------------------------------------------------------
staff_df = load_staff_data()
staff_json = df_to_json_records(staff_df)

VIDEO_URL = "https://raw.githubusercontent.com/usman4801/PXT-AI-ASSISTANT/main/banner.mp4"

KIOSK_HTML = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    *{box-sizing:border-box;margin:0;padding:0;}
    html,body{width:100%;height:100%;background:#05070c;font-family:'Segoe UI',Arial,sans-serif;overflow:hidden;color:#eaf6ff;}

    .kiosk{position:relative;width:100vw;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;overflow:hidden;padding-top:60px;}

    /* ----- background layers ----- */
    .bg-video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:0;opacity:.85;}
    .bg-grad{position:absolute;inset:0;z-index:0;
        background:radial-gradient(circle at 20% 30%,rgba(0,180,255,.15),transparent 45%),
                   radial-gradient(circle at 80% 70%,rgba(0,255,200,.12),transparent 45%),
                   linear-gradient(120deg,#05070c,#0a0f1a 40%,#05070c);
        background-size:200% 200%;animation:bgshift 18s ease-in-out infinite;}
    @keyframes bgshift{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
    .grid-ov{position:absolute;inset:0;z-index:0;
        background-image:linear-gradient(rgba(0,220,255,.05) 1px,transparent 1px),
                         linear-gradient(90deg,rgba(0,220,255,.05) 1px,transparent 1px);
        background-size:42px 42px;mask-image:radial-gradient(circle at 50% 40%,black 10%,transparent 75%);}
    .scrim{position:absolute;inset:0;z-index:1;background:radial-gradient(circle at 50% 45%,rgba(5,7,12,.15),rgba(5,7,12,.85) 75%);}

    /* ----- top bar ----- */
    .top-bar{position:fixed;top:0;left:0;right:0;z-index:5;display:flex;align-items:center;justify-content:space-between;padding:14px 24px;background:rgba(5,7,12,.5);backdrop-filter:blur(8px);}
    .mic-ind{display:flex;align-items:center;gap:8px;}
    .mic-dot{width:11px;height:11px;border-radius:50%;background:#ff5b5b;box-shadow:0 0 10px rgba(255,80,80,.8);transition:all .3s;}
    .mic-dot.on{background:#46ffb0;box-shadow:0 0 12px rgba(70,255,176,.9);}
    .mic-label{font-size:11px;color:#7fd0ef;letter-spacing:1px;text-transform:uppercase;}
    .debug{color:#7fd0ef;font-size:12px;letter-spacing:.3px;background:rgba(10,16,26,.6);padding:5px 14px;border-radius:999px;border:1px solid rgba(80,200,255,.2);max-width:55vw;text-align:center;opacity:.85;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}

    /* ----- brand ----- */
    .brand{position:relative;z-index:2;color:#e8f6ff;letter-spacing:6px;font-size:17px;font-weight:600;opacity:.7;margin:10px 0 16px;text-transform:uppercase;}

    /* ----- chat area ----- */
    .chat-area{position:relative;z-index:2;width:min(620px,92vw);flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:10px;padding:8px 4px 100px;scrollbar-width:thin;scrollbar-color:rgba(80,200,255,.3) transparent;}
    .chat-area::-webkit-scrollbar{width:4px;}
    .chat-area::-webkit-scrollbar-thumb{background:rgba(80,200,255,.3);border-radius:4px;}

    .bubble{max-width:82%;padding:12px 18px;border-radius:18px;font-size:14.5px;line-height:1.55;animation:pop .3s ease;}
    .bubble.ai{align-self:flex-start;background:rgba(15,22,34,.78);border:1px solid rgba(90,210,255,.22);backdrop-filter:blur(12px);box-shadow:0 0 18px rgba(0,150,255,.08);}
    .bubble.user{align-self:flex-end;background:rgba(0,130,255,.18);border:1px solid rgba(0,170,255,.3);backdrop-filter:blur(12px);}
    @keyframes pop{from{opacity:0;transform:translateY(8px) scale(.97)}to{opacity:1;transform:translateY(0) scale(1)}}

    /* result card */
    .rcard{max-width:88%;align-self:flex-start;background:rgba(15,22,34,.8);border:1px solid rgba(90,210,255,.3);border-radius:18px;padding:20px 26px;backdrop-filter:blur(14px);text-align:center;box-shadow:0 0 28px rgba(0,150,255,.1);animation:pop .35s ease;}
    .rcard .rn{font-size:21px;font-weight:700;margin-bottom:2px;}
    .rcard .ri{font-size:11.5px;letter-spacing:2px;color:#7fd8ff;opacity:.8;margin-bottom:14px;text-transform:uppercase;}
    .rcard .rg{display:flex;justify-content:space-around;gap:10px;flex-wrap:wrap;}
    .rcard .rg .ri-item .lbl{font-size:10px;letter-spacing:1.5px;color:#8fb8cf;text-transform:uppercase;margin-bottom:4px;}
    .rcard .rg .ri-item .val{font-size:16px;font-weight:600;}
    .c-pres{color:#4dffb0;} .c-abs{color:#ff6767;} .c-oth{color:#ffd166;}

    /* typing indicator */
    .typing{display:inline-flex;gap:4px;padding:4px 0;}
    .typing span{width:6px;height:6px;border-radius:50%;background:#7fd0ef;animation:tbounce .6s infinite alternate;}
    .typing span:nth-child(2){animation-delay:.15s;}
    .typing span:nth-child(3){animation-delay:.3s;}
    @keyframes tbounce{to{opacity:.3;transform:translateY(-4px)}}

    /* ----- bottom pill ----- */
    .pill{position:fixed;bottom:28px;left:50%;transform:translateX(-50%);z-index:4;display:flex;flex-direction:column;align-items:center;gap:3px;padding:11px 28px;border-radius:999px;background:rgba(10,16,26,.7);border:1px solid rgba(80,200,255,.3);backdrop-filter:blur(10px);text-align:center;max-width:90vw;transition:all .3s;}
    .pill.glow{animation:pillglow 2s ease-in-out infinite;}
    @keyframes pillglow{0%,100%{box-shadow:0 0 16px rgba(0,190,255,.25),inset 0 0 8px rgba(0,190,255,.05)}50%{box-shadow:0 0 32px rgba(0,190,255,.5),inset 0 0 14px rgba(0,190,255,.1)}}
    .pill .p1{color:#dff5ff;font-size:13.5px;font-weight:600;letter-spacing:.4px;}
    .pill .p2{color:#7fd0ef;font-size:11.5px;letter-spacing:.3px;opacity:.85;}

    /* ----- permission overlay ----- */
    .perm-overlay{position:fixed;inset:0;z-index:100;background:rgba(5,7,12,.92);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;backdrop-filter:blur(6px);}
    .perm-overlay h2{color:#eaf6ff;font-size:24px;font-weight:700;}
    .perm-overlay p{color:#8fb8cf;font-size:15px;max-width:400px;text-align:center;line-height:1.6;}
    .perm-btn{padding:14px 36px;border-radius:999px;border:1px solid rgba(0,190,255,.4);background:rgba(0,150,255,.15);color:#dff5ff;font-size:16px;font-weight:600;cursor:pointer;transition:all .2s;letter-spacing:.5px;}
    .perm-btn:hover{background:rgba(0,150,255,.3);box-shadow:0 0 20px rgba(0,190,255,.3);}
</style>
</head>
<body>

<!-- Permission overlay — user must click to allow mic + audio -->
<div class="perm-overlay" id="permOverlay">
    <h2>&#127897;&#65039; PXT Hub</h2>
    <p>Tap the button below to enable voice interaction. Your browser needs permission for the microphone and audio.</p>
    <button class="perm-btn" id="permBtn">Enable Voice Assistant</button>
</div>

<div class="kiosk" id="kiosk" style="display:none;">
    <video class="bg-video" id="bgVideo" autoplay loop playsinline style="display:none;"></video>
    <div class="bg-grad" id="bgGrad"></div>
    <div class="grid-ov"></div>
    <div class="scrim"></div>

    <div class="top-bar">
        <div class="mic-ind">
            <div class="mic-dot" id="micDot"></div>
            <div class="mic-label" id="micLabel">MIC OFF</div>
        </div>
        <div class="debug" id="debug">&nbsp;</div>
    </div>

    <div class="brand">PXT&nbsp;HUB</div>

    <div class="chat-area" id="chatArea"></div>

    <div class="pill" id="pill">
        <div class="p1" id="p1">PXT AI Assistant</div>
        <div class="p2" id="p2">Starting up...</div>
    </div>
</div>

<script>
(function(){

/* ========== DATA ========== */
const STAFF = __STAFF_JSON__;
const VIDEO_SRC = "__VIDEO_URL__";

/* ========== DOM ========== */
const $=id=>document.getElementById(id);
const micDot=$('micDot'),micLabel=$('micLabel'),debug=$('debug'),chatArea=$('chatArea');
const p1=$('p1'),p2=$('p2'),pill=$('pill');
const bgVideo=$('bgVideo'),bgGrad=$('bgGrad');
const permOverlay=$('permOverlay'),permBtn=$('permBtn'),kiosk=$('kiosk');

/* ========== SPEECH API CHECK ========== */
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
if(!SR){
    permOverlay.querySelector('p').textContent='Your browser does not support speech recognition. Please use Google Chrome or Microsoft Edge.';
    permBtn.style.display='none';
    return;
}

/* ========== STATE ========== */
let speaking=false;
let rec=null;
let shouldRun=true;
let lastActivity=Date.now();

/* ========== HELPERS ========== */
function norm(s){return(s||"").toLowerCase().trim().replace(/[^\p{L}\p{N}\s]/gu,"").replace(/\s+/g," ");}

function setPill(l1,l2,glow){
    p1.textContent=l1;p2.textContent=l2;
    pill.classList.toggle('glow',!!glow);
}

function setMic(on){
    micDot.classList.toggle('on',on);
    micLabel.textContent=on?'LISTENING':'MIC OFF';
}

function addBubble(text,who){
    const d=document.createElement('div');
    d.className='bubble '+who;
    d.textContent=text;
    chatArea.appendChild(d);
    chatArea.scrollTop=chatArea.scrollHeight;
    while(chatArea.children.length>30) chatArea.removeChild(chatArea.firstChild);
    return d;
}

function addTyping(){
    const d=document.createElement('div');
    d.className='bubble ai';d.id='typingB';
    d.innerHTML='<div class="typing"><span></span><span></span><span></span></div>';
    chatArea.appendChild(d);
    chatArea.scrollTop=chatArea.scrollHeight;
}
function removeTyping(){const t=$('typingB');if(t)t.remove();}

function addResultCard(s){
    const cls=s.status.toLowerCase().includes('present')?'c-pres':s.status.toLowerCase().includes('absent')?'c-abs':'c-oth';
    const d=document.createElement('div');
    d.className='rcard';
    d.innerHTML='<div class="rn">'+s.name+'</div><div class="ri">'+s.id+'</div>'
        +'<div class="rg">'
        +'<div class="ri-item"><div class="lbl">Status</div><div class="val '+cls+'">'+(s.status||'\u2014')+'</div></div>'
        +'<div class="ri-item"><div class="lbl">Leaves Left</div><div class="val">'+(s.leaves||'\u2014')+'</div></div>'
        +'<div class="ri-item"><div class="lbl">Next Off Day</div><div class="val">'+(s.nextoff||'\u2014')+'</div></div>'
        +'</div>';
    chatArea.appendChild(d);
    chatArea.scrollTop=chatArea.scrollHeight;
}

/* ========== TTS ========== */
function speak(text,lang,cb){
    speaking=true;
    try{window.speechSynthesis.cancel();}catch(e){}
    const u=new SpeechSynthesisUtterance(text);
    u.lang=lang||'en-US';u.rate=1.0;u.pitch=1.0;
    u.onend=()=>{speaking=false;if(cb)cb();};
    u.onerror=()=>{speaking=false;if(cb)cb();};
    window.speechSynthesis.speak(u);
    // safety timeout
    const maxMs=Math.max(text.length*85,3000)+4000;
    setTimeout(()=>{if(speaking){speaking=false;try{window.speechSynthesis.cancel();}catch(e){}if(cb)cb();}},maxMs);
}

/* ========== STAFF SEARCH (5-pass) ========== */
function findStaff(t){
    t=norm(t);const tn=t.replace(/\s+/g,"");
    if(!t||t.length<2)return null;
    // 1. ID exact
    for(const s of STAFF){const id=norm(s.id).replace(/\s+/g,"");if(id&&(tn.includes(id)||id.includes(tn)))return s;}
    // 2. Full name
    for(const s of STAFF){if(norm(s.name)&&t.includes(norm(s.name)))return s;}
    // 3. Aliases
    for(const s of STAFF){for(const a of(s.aliases||[])){if(norm(a)&&norm(a).length>1&&t.includes(norm(a)))return s;}}
    // 4. All name tokens
    for(const s of STAFF){const toks=norm(s.name).split(" ").filter(Boolean);if(toks.length>0&&toks.every(tok=>t.includes(tok)))return s;}
    // 5. Any single name token (3+ chars)
    for(const s of STAFF){const toks=norm(s.name).split(" ").filter(Boolean);if(toks.some(tok=>tok.length>=3&&t.split(" ").some(w=>w===tok)))return s;}
    return null;
}

/* ========== CONVERSATIONAL AI ========== */
function pick(arr){return arr[Math.floor(Math.random()*arr.length)];}

function getResponse(text){
    const t=norm(text);

    // ---- Staff lookup keywords ----
    const staffKW=["leave","leaves","chutti","chhutti","off day","week off","attendance","status","record","detail","info","punch","schedule","roster"];
    const hasStaffKW=staffKW.some(k=>t.includes(k));

    if(hasStaffKW){
        const staff=findStaff(t);
        if(staff) return {type:'staff',staff:staff};
        return {type:'ai',text:"Sure, I can check that for you! Just tell me the employee's name or ID."};
    }

    // ---- Direct name match (no keyword needed) ----
    const directMatch=findStaff(t);
    if(directMatch) return {type:'staff',staff:directMatch};

    // ---- Greetings ----
    if(/\b(hi|hello|hey|salam|assalam|namaste|hola|good morning|good afternoon|good evening)\b/.test(t)){
        return {type:'ai',text:pick([
            "Hello! Welcome to PXT Hub. I'm your AI assistant \u2014 ask me anything about employees, leaves, or just chat!",
            "Hey there! Great to have you here. I can look up attendance, leaves, schedules, or we can just talk. What's on your mind?",
            "Hi! I'm PXT, your voice assistant. Say any employee's name to see their details, or ask me anything!",
            "Assalam o Alaikum! How can I help you today? I can check employee records or just have a conversation."
        ])};
    }

    // ---- How are you ----
    if(/how are you|kaise ho|kya haal|kaisa hai|how do you do|how is it going/.test(t)){
        return {type:'ai',text:pick([
            "I'm doing fantastic, thanks for asking! What can I do for you today?",
            "Running at full power! Ready to help with anything you need.",
            "I'm great! I never get tired. Ask me about employees, or let's just chat!",
            "All systems go! How about you? Need any help?"
        ])};
    }

    // ---- What's your name / who are you ----
    if(/who are you|what are you|your name|kya hai tu|kaun ho|what is this/.test(t)){
        return {type:'ai',text:"I'm PXT Hub, your AI-powered voice assistant. I can check employee attendance, leave balances, next off days, tell you the time, crack a joke, or just have a friendly chat. Try me!"};
    }

    // ---- What can you do ----
    if(/what can you do|help|features|capabilities|kya kar sakt/.test(t)){
        return {type:'ai',text:"Here's what I can do: Check employee status and attendance. Show remaining leaves and next off day. Tell you the current time and date. Have a conversation. Crack jokes. Just say an employee's name or ask me anything!"};
    }

    // ---- Time ----
    if(/what time|kitne baje|time kya|current time|abhi time/.test(t)){
        const now=new Date();
        return {type:'ai',text:"It's currently "+now.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit'})+". Anything else I can help with?"};
    }

    // ---- Date ----
    if(/what date|today date|aaj date|what day|aaj kya din|today is/.test(t)){
        const now=new Date();
        return {type:'ai',text:"Today is "+now.toLocaleDateString('en-US',{weekday:'long',year:'numeric',month:'long',day:'numeric'})+". Need anything else?"};
    }

    // ---- Thank you ----
    if(/\b(thank|thanks|shukriya|dhanyawad|shukria|meharbani)\b/.test(t)){
        return {type:'ai',text:pick([
            "You're welcome! Always happy to help.",
            "No problem at all! Let me know if you need anything else.",
            "Anytime! I'm right here whenever you need me.",
            "My pleasure! What else can I do for you?"
        ])};
    }

    // ---- Goodbye ----
    if(/\b(bye|goodbye|alvida|khuda hafiz|see you|later|take care)\b/.test(t)){
        return {type:'ai',text:pick([
            "Goodbye! Have a wonderful day. I'll be right here when you need me!",
            "See you later! Take care and come back anytime.",
            "Bye bye! Wishing you a great day ahead."
        ])};
    }

    // ---- Jokes ----
    if(/\b(joke|funny|maza|hansi|laugh|entertain|bored)\b/.test(t)){
        return {type:'ai',text:pick([
            "Why did the employee bring a ladder to work? Because they wanted to reach new heights in their career!",
            "What's HR's favorite type of music? Staff notation!",
            "Why don't attendance systems ever win arguments? They always get clocked!",
            "What did the spreadsheet say to the employee? I've got your number!",
            "Why was the calendar always stressed? Because its days were numbered!"
        ])};
    }

    // ---- Weather ----
    if(/weather|mausam|barish|garmi|temperature|cold|hot/.test(t)){
        return {type:'ai',text:"I wish I could check the weather! I'm specialized in employee data, but I can tell you the time, check attendance, or keep you company with a joke. What would you prefer?"};
    }

    // ---- Good/praise ----
    if(/\b(good job|well done|nice|great|awesome|amazing|perfect|excellent)\b/.test(t)){
        return {type:'ai',text:pick([
            "Thank you! That means a lot. I'm always trying my best!",
            "Aww, thanks! You're pretty awesome yourself!",
            "I appreciate that! Let me know if there's anything else I can help with."
        ])};
    }

    // ---- Yes/No basic ----
    if(/^(yes|yeah|yep|no|nah|nope|okay|ok|sure|alright)$/.test(t)){
        return {type:'ai',text:pick([
            "Got it! What would you like to know?",
            "Alright! Feel free to ask me anything.",
            "Okay! I'm here and ready to help."
        ])};
    }

    // ---- Fallback ----
    return {type:'ai',text:pick([
        "Interesting! I'm best at employee info \u2014 attendance, leaves, and schedules. Want to check someone's details?",
        "I'm here to help! Say any employee's name and I'll pull up their info. Or ask me the time, a joke, or anything!",
        "I didn't quite catch what you need, but I'm all ears! Try asking about an employee, or say 'help' to see what I can do.",
        "Tell me more! You can ask about any employee by name, or we can just keep chatting."
    ])};
}

/* ========== MAIN RECOGNITION LOOP ========== */
function startListening(){
    if(!shouldRun||speaking)return;
    try{if(rec){rec.abort();}}catch(e){}

    rec=new SR();
    rec.continuous=true;
    rec.interimResults=true;
    rec.lang='en-US';
    rec.maxAlternatives=1;

    rec.onstart=()=>{
        setMic(true);
        debug.textContent='Listening...';
        setPill("I'm listening","Say anything \u2014 I'm always here",true);
    };

    rec.onend=()=>{
        setMic(false);
        if(shouldRun&&!speaking) setTimeout(startListening,350);
    };

    rec.onerror=(e)=>{
        setMic(false);
        debug.textContent='Mic: '+e.error;
        if(e.error==='not-allowed'){
            setPill("Microphone blocked","Please allow mic access in browser settings",false);
            return;
        }
        if(shouldRun&&!speaking) setTimeout(startListening,900);
    };

    rec.onresult=(event)=>{
        lastActivity=Date.now();
        let live="";
        for(let i=event.resultIndex;i<event.results.length;i++) live+=event.results[i][0].transcript;
        debug.textContent='Heard: '+live;

        const last=event.results[event.results.length-1];
        if(last.isFinal){
            const txt=last[0].transcript.trim();
            if(txt.length<2)return;
            handleInput(txt);
        }
    };

    try{rec.start();}catch(e){setTimeout(startListening,1200);}
}

/* ========== HANDLE INPUT ========== */
function handleInput(text){
    try{rec.stop();}catch(e){}
    setMic(false);

    addBubble(text,'user');
    addTyping();
    setPill("Processing...","Thinking...",false);

    setTimeout(()=>{
        removeTyping();
        const resp=getResponse(text);

        if(resp.type==='staff'){
            const s=resp.staff;
            addResultCard(s);
            const msg="Here are the details for "+s.name+". Status: "+s.status+". Remaining leaves: "+s.leaves+". Next off day: "+s.nextoff+".";
            addBubble(msg,'ai');
            setPill(s.name,"Showing details",false);
            speak(msg,'en-US',()=>{
                setPill("I'm listening","Ask me anything else",true);
                startListening();
            });
        } else {
            addBubble(resp.text,'ai');
            setPill("PXT Assistant","Responding...",false);
            speak(resp.text,'en-US',()=>{
                setPill("I'm listening","Say anything \u2014 I'm always here",true);
                startListening();
            });
        }
    },500);
}

/* ========== WATCHDOG ========== */
setInterval(()=>{
    if(!speaking&&shouldRun&&Date.now()-lastActivity>15000){
        debug.textContent="Refreshing mic...";
        try{if(rec)rec.abort();}catch(e){}
        setTimeout(startListening,500);
        lastActivity=Date.now();
    }
},6000);

/* ========== PERMISSION GATE ========== */
permBtn.addEventListener('click',()=>{
    permOverlay.style.display='none';
    kiosk.style.display='flex';

    // Start video with audio
    if(VIDEO_SRC){
        bgVideo.src=VIDEO_SRC;
        bgVideo.style.display="block";
        bgVideo.muted=false;
        bgVideo.volume=0.25;
        bgVideo.play().then(()=>{
            if(bgGrad)bgGrad.style.display="none";
        }).catch(()=>{
            bgVideo.muted=true;
            bgVideo.play().catch(()=>{});
        });
    }

    // Warm up TTS
    try{const w=new SpeechSynthesisUtterance(' ');w.volume=0;window.speechSynthesis.speak(w);}catch(e){}

    // Welcome greeting
    setTimeout(()=>{
        const greet="Welcome to PXT Hub! I'm your AI voice assistant. You can ask me about any employee, check leaves and attendance, or just have a conversation. Go ahead, I'm listening!";
        addBubble(greet,'ai');
        speak(greet,'en-US',()=>{startListening();});
    },800);
});

/* ========== CLEANUP ========== */
window.addEventListener('beforeunload',()=>{
    shouldRun=false;
    try{if(rec)rec.stop();}catch(e){}
    try{window.speechSynthesis.cancel();}catch(e){}
});

})();
</script>
</body>
</html>
"""

# --------------------------------------------------------------------------
# INJECT DATA INTO HTML & RENDER
# --------------------------------------------------------------------------
KIOSK_HTML = KIOSK_HTML.replace("__STAFF_JSON__", staff_json)
KIOSK_HTML = KIOSK_HTML.replace("__VIDEO_URL__", VIDEO_URL)

st.components.v1.html(KIOSK_HTML, height=1000, scrolling=False)
