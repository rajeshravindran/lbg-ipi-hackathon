/* ============================================================
   AVIVA CHAT – Client-side chat logic
   Handles communication with the FastAPI /api/chat endpoint
   and manages the chat UI state.
   ============================================================ */

// ---- State --------------------------------------------------
let sessionId = null;
let isChatOpen = false;
let isWaitingForResponse = false;

// ---- DOM Elements -------------------------------------------
const chatPanel = document.getElementById('chatPanel');
const chatToggle = document.getElementById('chatToggle');
const chatToggleIcon = document.getElementById('chatToggleIcon');
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const typingIndicator = document.getElementById('typingIndicator');

// Generate a session ID for this browser tab
sessionId = 'sess_' + Math.random().toString(36).substring(2, 15);

// ---- Chat Toggle --------------------------------------------
function toggleChat() {
    isChatOpen = !isChatOpen;
    chatPanel.classList.toggle('open', isChatOpen);
    chatToggleIcon.textContent = isChatOpen ? '✕' : '💬';

    if (isChatOpen) {
        chatInput.focus();
    }
}

function openChat() {
    if (!isChatOpen) {
        toggleChat();
    }
}

function openChatWithMessage(message) {
    openChat();
    // Small delay to let the panel animation complete
    setTimeout(() => {
        sendQuickMessage(message);
    }, 400);
}

// ---- Send Message -------------------------------------------
async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || isWaitingForResponse) return;

    // Add user message to chat
    appendMessage(text, 'user');

    // Clear input
    chatInput.value = '';
    autoResize(chatInput);
    sendBtn.disabled = true;

    // Show typing indicator
    showTyping();
    isWaitingForResponse = true;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                session_id: sessionId,
            }),
        });

        const data = await response.json();

        hideTyping();
        isWaitingForResponse = false;

        if (response.ok && data.response) {
            appendMessage(data.response, 'bot');

            // Update session ID if returned
            if (data.session_id) {
                sessionId = data.session_id;
            }
        } else {
            appendMessage(
                data.error || "I'm sorry, something went wrong. Please try again.",
                'bot'
            );
        }
    } catch (error) {
        hideTyping();
        isWaitingForResponse = false;
        console.error('Chat error:', error);
        appendMessage(
            "I'm sorry, I wasn't able to connect to the server. Please check your connection and try again.",
            'bot'
        );
    }
}

function sendQuickMessage(text) {
    chatInput.value = text;
    sendMessage();
}

// ---- Message Rendering --------------------------------------
function appendMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.textContent = sender === 'bot' ? 'A' : 'U';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Format the text — handle markdown-like formatting
    const formattedText = formatResponse(text);
    contentDiv.innerHTML = formattedText;

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);

    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function formatResponse(text) {
    // Convert markdown-style formatting to HTML
    let html = text;

    // Bold: **text** → <strong>text</strong>
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Italic: *text* → <em>text</em>
    html = html.replace(/(?<!\*)\*(?!\*)(.*?)\*(?!\*)/g, '<em>$1</em>');

    // Bullet points: - item → <li>item</li>
    html = html.replace(/^[-•]\s+(.+)$/gm, '<li>$1</li>');
    // Wrap consecutive <li> in <ul>
    html = html.replace(/((?:<li>.*?<\/li>\n?)+)/g, '<ul>$1</ul>');

    // Numbered lists: 1. item → wrapped similarly
    html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');

    // Split by double newlines into paragraphs
    const paragraphs = html.split(/\n\n+/);
    html = paragraphs
        .map(p => {
            p = p.trim();
            if (!p) return '';
            // Don't wrap if already has block elements
            if (p.startsWith('<ul>') || p.startsWith('<li>') || p.startsWith('<h')) {
                return p;
            }
            // Replace single newlines with <br>
            return '<p>' + p.replace(/\n/g, '<br>') + '</p>';
        })
        .join('');

    return html;
}

// ---- Typing Indicator ----------------------------------------
function showTyping() {
    typingIndicator.style.display = 'flex';
    scrollToBottom();
}

function hideTyping() {
    typingIndicator.style.display = 'none';
}

// ---- Input Handling -----------------------------------------
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';

    // Enable/disable send button
    sendBtn.disabled = !el.value.trim() || isWaitingForResponse;
}

// Enable send button when input changes
chatInput.addEventListener('input', () => {
    sendBtn.disabled = !chatInput.value.trim() || isWaitingForResponse;
});

// ---- Utilities -----------------------------------------------
function scrollToBottom() {
    requestAnimationFrame(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
}

function resetChat() {
    // Generate a new session ID
    sessionId = 'sess_' + Math.random().toString(36).substring(2, 15);

    // Clear all messages except the welcome message
    const welcomeMsg = document.getElementById('welcomeMessage');
    chatMessages.innerHTML = '';
    if (welcomeMsg) {
        chatMessages.appendChild(welcomeMsg);
    } else {
        // Recreate the welcome message
        const welcomeHtml = `
            <div class="message bot-message" id="welcomeMessage">
                <div class="message-avatar">A</div>
                <div class="message-content">
                    <p>Hello! 👋 Welcome to <strong>Aviva Insurance</strong>.</p>
                    <p>I'm your virtual insurance assistant, here to help you with all your insurance needs.</p>
                    <p>How can I help you today?</p>
                    <div class="quick-actions">
                        <button class="quick-action-btn" onclick="sendQuickMessage('I want a new car insurance quote')">🚗 Car quote</button>
                        <button class="quick-action-btn" onclick="sendQuickMessage('I want a new home insurance quote')">🏠 Home quote</button>
                        <button class="quick-action-btn" onclick="sendQuickMessage('I want to manage my existing policy')">📋 My policy</button>
                    </div>
                </div>
            </div>
        `;
        chatMessages.innerHTML = welcomeHtml;
    }

    hideTyping();
    isWaitingForResponse = false;
}

// ---- Wire up "Log in" and "Get a quote" nav buttons ----------
document.getElementById('btnLogin')?.addEventListener('click', () => {
    openChatWithMessage('I am an existing customer and want to log in');
});
document.getElementById('btnGetQuote')?.addEventListener('click', () => {
    openChatWithMessage('I want to get an insurance quote');
});
