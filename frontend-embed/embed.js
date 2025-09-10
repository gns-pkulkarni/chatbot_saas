// == Embed.js - Inject Chatbot Widget == //

const chatHistory = [];

(function () {

    let clientId = null;
    const scripts = document.getElementsByTagName('script');
    for (let s of scripts) {
        if (s.src.includes('embed.js') && s.src.includes('id=')) {
            const url = new URL(s.src);
            clientId = url.searchParams.get('id');
            break;
        }
    }
    if (!clientId) return console.error("Client ID not provided in embed script.");

    // Check subscription status first
    fetch(`http://localhost:8000/check-subscription/${clientId}`)
        .then(response => response.json())
        .then(data => {
            if (!data.valid || !data.active) {
                console.warn(`Chatbot not displayed: ${data.message}`);
                // Optionally, you can show a message to the website owner
                if (data.expired) {
                    console.error(`Subscription expired on ${data.end_date}. Please renew to continue using the chatbot.`);
                }
                return; // Don't initialize the chatbot
            }
            // Store plan details globally for feature checks
            window.cbt_plan = data.plan || {};
            // If subscription is valid, proceed with initialization
            initializeChatbot();
        })
        .catch(error => {
            console.error("Error checking subscription status:", error);
            // Optionally, you might want to not show the chatbot if there's an error
            return;
        });

    function initializeChatbot() {

    // Load CSS dynamically
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "http://localhost:8000/static/chatbot.css";
    document.head.appendChild(link);

    // Add Bootstrap CSS (Optional if needed for layout or utilities)
    const bootstrapLink = document.createElement("link");
    bootstrapLink.rel = "stylesheet";
    bootstrapLink.href = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css";
    bootstrapLink.integrity = "sha384-GtvZtJevxQ7uvylBxzEY2yDLxGqlFbI1kgz4ms1HP4oTzvKj40O0I9jFv5zNABf9";
    bootstrapLink.crossOrigin = "anonymous";
    document.head.appendChild(bootstrapLink);

    const emojiFontLink = document.createElement("link");
    emojiFontLink.rel = "stylesheet";
    emojiFontLink.href = "https://fonts.googleapis.com/css?family=Open+Sans:300,300i,400,400i,600,600i,700,700i|Raleway:300,300i,400,400i,500,500i,600,600i,700,700i|Poppins:300,300i,400,400i,500,500i,600,600i,700,700i";
    document.head.appendChild(emojiFontLink);

    const markedScript = document.createElement("script");
    markedScript.src = "https://cdn.jsdelivr.net/npm/marked/marked.min.js";
    document.head.appendChild(markedScript);

    // Create chatbot container wrapper
    const wrapper = document.createElement("div");
    wrapper.innerHTML = `
    <div id="chatbar" class="animation-chatbot">
      <img src="http://localhost:8000/static/images/chatbot.jpg" alt="Chatbot" />
      <div class="label">Chat with Pinak</div>
    </div>

    <div id="chatbox">
      <div id="chat-header">
        <div class="left">
          <img src="http://localhost:8000/static/images/chatbot.jpg" alt="Pinak" />
          <div>
            <strong>Pinak</strong><br />
            <small style="font-weight: 300;">AI Assistant</small>
          </div>
        </div>
        <div class="close" id="close-chat">&times;</div>
      </div>
      <div id="chat-body">
        <div class="bot-msg">Hello! How can I assist you today?</div>
      </div>
      <div id="chat-footer">
        <input type="text" id="user-input" placeholder="Type your message..." />
        <button id="mic-btn" title="Click to start recording" style="display:none;">
          <svg id="mic-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
            <path d="M3.5 6.5A.5.5 0 0 1 4 7v1a4 4 0 0 0 8 0V7a.5.5 0 0 1 1 0v1a5 5 0 0 1-4.5 4.975V15h3a.5.5 0 0 1 0 1h-7a.5.5 0 0 1 0-1h3v-2.025A5 5 0 0 1 3 8V7a.5.5 0 0 1 .5-.5z"/>
            <path d="M10 8a2 2 0 1 1-4 0V3a2 2 0 1 1 4 0v5zM8 0a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V3a3 3 0 0 0-3-3z"/>
          </svg>
          <svg id="stop-icon" style="display:none;" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
            <path d="M2 2h12v12H2z"/>
          </svg>
        </button>
        <button id="sendBtn">&#9658;</button>
      </div>
      <div class="gns-power">Powered by GNS AI</div>
    </div>`;

    document.body.appendChild(wrapper);

    // Get elements
    const chatbar = document.getElementById("chatbar");
    const chatbox = document.getElementById("chatbox");
    const closeBtn = document.getElementById("close-chat");
    const sendBtn = document.getElementById("sendBtn");
    const input = document.getElementById("user-input");
    const chatBody = document.getElementById("chat-body");
    const micBtn = document.getElementById("mic-btn");
    
    // Show mic button if plan allows voice
    if (window.cbt_plan?.can_use_voice) {
        micBtn.style.display = 'inline-block';
        initializeSpeechRecognition();
    }

    // Send message when Enter is pressed
    input.addEventListener("keypress", function (event) {
        if (event.key === "Enter") {
            sendBtn.click();
        }
    });

    chatbar.onclick = () => {
        chatbox.style.display = "flex";
        chatbar.style.display = "none";
    };

    closeBtn.onclick = () => {
        chatbox.style.display = "none";
        chatbar.style.display = "block";
    };

    sendBtn.onclick = async () => {
        const msg = input.value.trim();
        if (!msg) return;

        appendMessage("user", msg);
        input.value = "";
        
        // Reset speech recognition transcript and finalTranscript if it exists
        if (window.speechRecognitionTranscript) {
            window.speechRecognitionTranscript = '';
        }
        if (window.speechRecognitionFinalTranscript !== undefined) {
            window.speechRecognitionFinalTranscript = '';
        }
        
        showTyping();

        try {
            const response = await fetch("http://localhost:8000/chat/public/ask", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    user_id: clientId,
                    message: msg,
                    chat_history: chatHistory,
                }),
            });

            const data = await response.json();
            hideTyping();
            const answer = data.response || "I'm sorry, I did not get that.";
            appendMessage("bot", answer);
            chatHistory.push(["user", msg], ["bot", answer]);
        } catch (err) {
            hideTyping();
            appendMessage("bot", "Oops! Something went wrong.");
        }
    };

    function appendMessage(sender, text) {
        const msgDiv = document.createElement("div");
        msgDiv.className = sender === "bot" ? "bot-msg" : "user-msg";
        // msgDiv.innerHTML = text;
        msgDiv.innerHTML = marked.parse(text);
        chatBody.appendChild(msgDiv);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function showTyping() {
        const typing = document.createElement("div");
        typing.className = "typing-indicator";
        typing.id = "typing";
        typing.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
        chatBody.appendChild(typing);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function hideTyping() {
        const typing = document.getElementById("typing");
        if (typing) typing.remove();
    }
    
    // Initialize Speech Recognition for voice feature
    function initializeSpeechRecognition() {
        // Check for browser support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {
            console.log('Speech recognition not supported in this browser');
            micBtn.style.display = 'none';
            return;
        }
        
        const recognition = new SpeechRecognition();
        recognition.continuous = true;  // Keep listening until stopped
        recognition.interimResults = true;
        recognition.lang = 'en-US';
        
        let isRecording = false;
        let finalTranscript = '';
        const micIcon = document.getElementById('mic-icon');
        const stopIcon = document.getElementById('stop-icon');
        
        // Store transcript globally so it can be reset when message is sent
        window.speechRecognitionTranscript = '';
        window.speechRecognitionFinalTranscript = '';
        
        // Handle mic button click - toggle recording
        micBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            
            if (isRecording) {
                // Stop recording
                stopRecording();
            } else {
                // Start recording
                await startRecording();
            }
        });
        
        async function startRecording() {
            try {
                // Clear previous transcript
                finalTranscript = '';
                window.speechRecognitionTranscript = '';
                window.speechRecognitionFinalTranscript = '';
                input.value = '';
                
                // Start recognition
                recognition.start();
                isRecording = true;
                
                // Update UI
                micBtn.classList.add('recording');
                micBtn.style.backgroundColor = '#dc3545';  // Bootstrap danger color (red)
                micBtn.title = 'Click to stop recording';
                micIcon.style.display = 'none';
                stopIcon.style.display = 'block';
                
                console.log('Recording started');
            } catch (err) {
                console.error('Error starting recognition:', err);
                if (err.name === 'NotAllowedError') {
                    alert('Microphone access denied. Please allow microphone access in your browser settings and reload the page.');
                    micBtn.style.display = 'none';
                } else {
                    alert('Error starting voice recognition. Please try again.');
                }
                resetRecordingState();
            }
        }
        
        function stopRecording() {
            if (!isRecording) return;
            
            try {
                recognition.stop();
                console.log('Recording stopped');
            } catch (err) {
                console.error('Error stopping recognition:', err);
            }
            
            resetRecordingState();
        }
        
        function resetRecordingState() {
            isRecording = false;
            micBtn.classList.remove('recording');
            micBtn.style.backgroundColor = '';
            micBtn.title = 'Click to start recording';
            micIcon.style.display = 'block';
            stopIcon.style.display = 'none';
        }
        
        // Handle speech recognition results
        recognition.onresult = function(event) {
            let interimTranscript = '';
            
            // Check if we need to reset finalTranscript based on global state
            if (window.speechRecognitionFinalTranscript === '') {
                finalTranscript = '';
            }
            
            // Process all results from the last result index
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + ' ';
                } else {
                    interimTranscript += transcript;
                }
            }
            
            // Update global transcript and input field
            window.speechRecognitionTranscript = finalTranscript;
            window.speechRecognitionFinalTranscript = finalTranscript;
            console.log("Final Transcript -- " + finalTranscript);
            console.log("Interim Transcript -- " + interimTranscript);
            input.value = (finalTranscript + interimTranscript).trim();
        };
        
        // Handle recognition start
        recognition.onstart = function() {
            console.log('Speech recognition started');
        };
        
        // Handle speech end
        recognition.onend = function() {
            console.log('Speech recognition ended');
            
            // Only reset state if we're still recording (wasn't manually stopped)
            if (isRecording) {
                resetRecordingState();
            }
            
            // Don't auto-send, let user review and send manually
            if (input.value.trim()) {
                // Focus on input so user can edit if needed
                input.focus();
            }
        };
        
        // Handle errors
        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
            
            if (event.error === 'no-speech') {
                // Don't show alert for no-speech, just log it
                console.log('No speech detected - continue listening...');
                // Don't reset state, keep listening
                return;
            } else if (event.error === 'not-allowed' || event.error === 'permission-denied') {
                alert('Microphone access denied. Please allow microphone access in your browser settings and reload the page.');
                micBtn.style.display = 'none';
            } else if (event.error === 'network') {
                alert('Network error - speech recognition requires internet connection.');
            } else if (event.error === 'aborted') {
                console.log('Speech recognition aborted');
            }
            
            resetRecordingState();
        };
        
        // Add visual feedback styles
        const style = document.createElement('style');
        style.textContent = `
            #mic-btn {
                transition: background-color 0.3s ease;
                position: relative;
            }
            #mic-btn.recording {
                animation: pulse 1.5s infinite;
            }
            #mic-btn.recording::after {
                content: '';
                position: absolute;
                top: -2px;
                left: -2px;
                right: -2px;
                bottom: -2px;
                border: 2px solid #dc3545;
                border-radius: 4px;
                animation: pulse-border 1.5s infinite;
            }
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            @keyframes pulse-border {
                0% { opacity: 1; }
                50% { opacity: 0.5; }
                100% { opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
    
    } // End of initializeChatbot function
})();
