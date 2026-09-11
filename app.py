components.html(
    f"""
    <script>
    (function() {{
        try {{
            if (window.frameElement) {{
                window.frameElement.setAttribute("allow", "microphone; speech-recognition;");
            }}

            const pdoc = window.parent.document;
            const dot = pdoc.getElementById('micDot');
            const statusLabel = pdoc.getElementById('statusLabel');
            const bottomPill = pdoc.getElementById('bottomPill');
            const hologramStage = pdoc.getElementById('hologramStage');

            const currentKioskState = "{current_state}";
            const textToSay = "{speak_text_js}";

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            
            if (!SpeechRecognition) {{
                if (statusLabel) statusLabel.innerText = "CHROME NEEDED";
                if (bottomPill) bottomPill.innerText = "⚠️ Voice requires Google Chrome";
                return;
            }}

            let recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            let isSpeaking = false;
            let isRecognizing = false;

            function updateUI(listening, customText) {{
                if (!dot || !statusLabel || !bottomPill || !hologramStage) return;
                if (listening) {{
                    dot.className = 'dot listening';
                    statusLabel.className = 'status-txt listening';
                    statusLabel.innerText = 'LISTENING...';
                    hologramStage.classList.add('listening');
                    bottomPill.classList.add('listening');
                    if (customText) bottomPill.innerText = customText;
                }} else {{
                    dot.className = 'dot';
                    statusLabel.className = 'status-txt';
                    statusLabel.innerText = 'STANDBY';
                    hologramStage.classList.remove('listening');
                    bottomPill.classList.remove('listening');
                    if (currentKioskState === 'idle') {{
                        bottomPill.innerText = '🎙️ Say "Hi PXT" or Click here';
                    }} else if (currentKioskState === 'asked_badge') {{
                        bottomPill.innerText = '🎙️ Speak Badge Number (e.g. EMP011)';
                    }} else {{
                        bottomPill.innerText = '🎙️ Ask: "Leaves" or "Next off"';
                    }}
                }}
            }}

            function triggerBackend(val) {{
                if (isSpeaking) return;
                try {{ recognition.stop(); }} catch(e) {{}}
                const currentUrl = new URL(window.parent.location.href);
                currentUrl.searchParams.set('voice_payload', val);
                window.parent.location.href = currentUrl.toString();
            }}

            recognition.onstart = function() {{
                isRecognizing = true;
                updateUI(true);
            }};

            recognition.onresult = function(event) {{
                if (isSpeaking) return;

                let liveText = '';
                let isFinal = false;

                for (let i = event.resultIndex; i < event.results.length; ++i) {{
                    liveText += event.results[i][0].transcript;
                    if (event.results[i].isFinal) isFinal = true;
                }}

                liveText = liveText.trim();
                const lower = liveText.toLowerCase();

                // Live feedback screen par dikhana taake pata chale mic sun raha hai
                if (liveText.length > 0) {{
                    updateUI(true, 'Heard: "' + liveText + '"');
                }}

                if (currentKioskState === 'idle') {{
                    // Chrome PXT ko aksar txt, bxt, pic, ya pxd sunta hai
                    const normalized = lower.replace(/[^a-z]/g, '');
                    const isWakeTrigger = 
                        normalized.includes('pxt') || 
                        normalized.includes('pxd') || 
                        normalized.includes('txt') || 
                        normalized.includes('hipxt') || 
                        normalized.includes('hello') ||
                        normalized.includes('hub');

                    if (isWakeTrigger) {{
                        triggerBackend('WAKE');
                    }}
                }} else if (isFinal && liveText.length > 0) {{
                    triggerBackend(liveText);
                }}
            }};

            recognition.onerror = function(event) {{
                // no-speech aam baat hai, isko error ki tarah crash nahi hone dena
                if (event.error !== 'no-speech') {{
                    console.log('Recognition Status:', event.error);
                }}
                if (event.error === 'not-allowed') {{
                    if (statusLabel) statusLabel.innerText = 'MIC BLOCKED';
                    if (bottomPill) bottomPill.innerText = '🔒 Click to Allow Mic';
                }}
            }};

            recognition.onend = function() {{
                isRecognizing = false;
                if (!isSpeaking) {{
                    updateUI(false);
                    // Silently restart taake Standby loop tootne na paye
                    setTimeout(safeStart, 200);
                }}
            }};

            function safeStart() {{
                if (!isRecognizing && !isSpeaking) {{
                    try {{
                        recognition.start();
                    }} catch(e) {{}}
                }}
            }}

            // Bottom pill par direct click se wake trigger (Gesture fallback)
            if (bottomPill) {{
                bottomPill.onclick = function() {{
                    if (currentKioskState === 'idle') {{
                        triggerBackend('WAKE');
                    }} else {{
                        safeStart();
                    }}
                }};
            }}

            // TTS greeting agar hai to pehle sunaye, phir mic activate kare
            if (textToSay && 'speechSynthesis' in window) {{
                isSpeaking = true;
                window.speechSynthesis.cancel();
                const ut = new SpeechSynthesisUtterance(textToSay);
                ut.rate = 0.95;
                ut.onend = function() {{
                    isSpeaking = false;
                    safeStart();
                }};
                ut.onerror = function() {{
                    isSpeaking = false;
                    safeStart();
                }};
                window.speechSynthesis.speak(ut);
            }} else {{
                safeStart();
            }}

        }} catch(err) {{
            console.log('Bridge error:', err);
        }}
    }})();
    </script>
    """,
    height=0,
)
