/**
 * Chat Widget JavaScript
 * Handles all chat functionality including sending/receiving messages,
 * file uploads, fullscreen mode, and real-time updates
 */

let chatWindow = null;
let chatMessages = null;
let chatMessageInput = null;
let chatFileInput = null;
let chatFilePreview = null;
let chatFileName = null;
let chatUnreadBadge = null;
let chatSendBtn = null;
let isFullscreen = false;
let selectedFile = null;
let currentUserId = null;
let pollInterval = null;
let lastMessageId = 0;

// Initialize chat when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
        console.log("Chat: DOMContentLoaded fired, initializing...");
        initChat();
    });
} else {
    console.log("Chat: DOM is already ready, initializing immediately...");
    initChat();
}

console.log("Chat: chat.js script loaded");

// Initialize configuration from DOM data attributes
function getConfig() {
    try {
        const dataEl = document.getElementById('chat-session-data');
        if (dataEl) {
            console.log("Chat: Found session data element");
            return {
                userId: JSON.parse(dataEl.dataset.userId || "0"),
                userName: JSON.parse(dataEl.dataset.userName || '"Guest"'),
                userRole: JSON.parse(dataEl.dataset.userRole || '"staff"')
            };
        }
        console.warn("Chat: #chat-session-data element not found, using defaults");
    } catch (e) {
        console.error("Chat: Error parsing session data:", e);
    }
    return { userId: 0, userName: 'Guest', userRole: 'staff' };
}

try {
    window.chatConfig = getConfig();
    console.log("Chat: Configuration initialized", window.chatConfig);
} catch (e) {
    console.error("Chat: Failed to initialize window.chatConfig", e);
    window.chatConfig = { userId: 0, userName: 'Guest', userRole: 'staff' };
}

// Global alias for compatibility with sidebar
window.openChat = function () {
    console.log("Chat: window.openChat called");
    try {
        if (!chatWindow) {
            console.log("Chat: Re-initializing elements...");
            initChat();
        }

        if (chatWindow) {
            if (!chatWindow.classList.contains('active')) {
                toggleChat();
            } else {
                console.log("Chat: Chat window already active");
            }
        } else {
            console.error("Chat: chatWindow still not found after re-init");
        }
    } catch (e) {
        console.error("Chat: Error in openChat:", e);
    }
};

function initChat() {
    // Get DOM elements
    chatWindow = document.getElementById('chatWindow');
    chatMessages = document.getElementById('chatMessages');
    chatMessageInput = document.getElementById('chatMessageInput');
    chatFileInput = document.getElementById('chatFileInput');
    chatFilePreview = document.getElementById('chatFilePreview');
    chatFileName = document.getElementById('chatFileName');
    chatUnreadBadge = document.getElementById('chatUnreadBadge');
    chatSendBtn = document.getElementById('chatSendBtn');

    if (!chatWindow) {
        console.warn("Chat: chatWindow element not found!");
        return;
    }

    console.log("Chat: Elements initialized successfully");

    // Load initial messages
    loadMessages();

    // Start polling for new messages every 3 seconds
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(loadMessages, 3000);

    // Update unread count
    updateUnreadCount();
    setInterval(updateUnreadCount, 5000);
}

function toggleChat() {
    console.log("Chat: toggleChat called");
    if (!chatWindow) {
        initChat();
    }

    if (!chatWindow) {
        console.error("Chat: Cannot toggle chat, chatWindow not found");
        return;
    }

    if (chatWindow.classList.contains('active')) {
        chatWindow.classList.remove('active');
    } else {
        chatWindow.classList.add('active');
        loadMessages();
        scrollToBottom();
        // Mark messages as read when opening chat
        markMessagesAsRead();
    }
}

function toggleFullscreen() {
    isFullscreen = !isFullscreen;
    const fullscreenIcon = document.getElementById('fullscreenIcon');

    if (isFullscreen) {
        chatWindow.classList.add('fullscreen');
        fullscreenIcon.textContent = '⛶';
    } else {
        chatWindow.classList.remove('fullscreen');
        fullscreenIcon.textContent = '⛶';
    }

    setTimeout(scrollToBottom, 300);
}

function handleKeyPress(event) {
    // Send message on Enter (without Shift)
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage(event);
    }
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        selectedFile = file;
        chatFileName.textContent = file.name;
        chatFilePreview.classList.add('active');
    }
}

function removeFile() {
    selectedFile = null;
    chatFileInput.value = '';
    chatFilePreview.classList.remove('active');
}

async function sendMessage(event) {
    if (event) {
        event.preventDefault();
    }

    const message = chatMessageInput.value.trim();

    if (!message && !selectedFile) {
        return;
    }

    // Disable send button
    chatSendBtn.disabled = true;

    try {
        const formData = new FormData();
        if (message) {
            formData.append('message', message);
        }
        if (selectedFile) {
            formData.append('file', selectedFile);
        }

        const response = await fetch('/api/chat/send', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            // Clear input
            chatMessageInput.value = '';
            removeFile();

            // Reload messages
            await loadMessages();
            scrollToBottom();
        } else {
            const error = await response.json();
            alert('Error sending message: ' + (error.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error sending message:', error);
        alert('Error sending message. Please try again.');
    } finally {
        chatSendBtn.disabled = false;
        chatMessageInput.focus();
    }
}

async function loadMessages() {
    try {
        const response = await fetch('/api/chat/messages?limit=100');
        if (!response.ok) {
            throw new Error('Failed to load messages');
        }

        const data = await response.json();
        const messages = data.messages || [];

        if (messages.length === 0) {
            chatMessages.innerHTML = `
                <div class="chat-empty">
                    <div class="chat-empty-icon">💬</div>
                    <p class="chat-empty-text">No messages yet. Start the conversation!</p>
                </div>
            `;
            return;
        }

        // Check if there are new messages
        const hasNewMessages = messages.length > 0 &&
            messages[messages.length - 1].id > lastMessageId;

        if (hasNewMessages) {
            lastMessageId = messages[messages.length - 1].id;
        }

        // Render messages
        chatMessages.innerHTML = messages.map(msg => renderMessage(msg)).join('');

        // Auto-scroll if chat is open and there are new messages
        if (chatWindow.classList.contains('active') && hasNewMessages) {
            scrollToBottom();
        }
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

function renderMessage(msg) {
    const currentUserIdFromConfig = window.chatConfig ? window.chatConfig.userId : null;
    const isOwn = msg.sender_id == currentUserIdFromConfig;
    const messageClass = isOwn ? 'own' : 'other';

    const time = formatTime(msg.timestamp);
    const initials = getInitials(msg.sender_name);
    const roleClass = msg.sender_role || 'staff';

    let fileHtml = '';
    if (msg.file_path) {
        if (msg.file_type === 'image') {
            fileHtml = `
                <a href="${msg.file_path}" target="_blank">
                    <img src="${msg.file_path}" alt="${msg.file_name}" class="message-file-image">
                </a>
            `;
        } else {
            const fileIcon = getFileIcon(msg.file_type);
            fileHtml = `
                <div class="message-file">
                    <span class="message-file-icon">${fileIcon}</span>
                    <div class="message-file-info">
                        <p class="message-file-name">
                            <a href="${msg.file_path}" target="_blank" class="message-file-link">
                                ${msg.file_name}
                            </a>
                        </p>
                    </div>
                </div>
            `;
        }
    }

    return `
        <div class="message ${messageClass}">
            <div class="message-header">
                <div class="message-avatar ${roleClass}">${initials}</div>
                <span class="message-sender">${msg.sender_name}</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-bubble">
                ${msg.message ? `<p class="message-text">${escapeHtml(msg.message)}</p>` : ''}
                ${fileHtml}
            </div>
        </div>
    `;
}

function getInitials(name) {
    if (!name) return '?';
    const parts = name.split(' ');
    if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
}

function getFileIcon(fileType) {
    const icons = {
        'pdf': '📄',
        'doc': '📝',
        'docx': '📝',
        'txt': '📝',
        'image': '🖼️',
        'other': '📎'
    };
    return icons[fileType] || icons['other'];
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    // Less than 1 minute
    if (diff < 60000) {
        return 'Just now';
    }

    // Less than 1 hour
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes}m ago`;
    }

    // Less than 24 hours
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours}h ago`;
    }

    // Show date
    const options = { month: 'short', day: 'numeric' };
    if (date.getFullYear() !== now.getFullYear()) {
        options.year = 'numeric';
    }
    return date.toLocaleDateString('en-US', options);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

async function updateUnreadCount() {
    try {
        const response = await fetch('/api/chat/unread');
        if (response.ok) {
            const data = await response.json();
            const count = data.count || 0;

            if (count > 0) {
                chatUnreadBadge.textContent = count > 99 ? '99+' : count;
                chatUnreadBadge.style.display = 'flex';
            } else {
                chatUnreadBadge.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error updating unread count:', error);
    }
}

async function markMessagesAsRead() {
    try {
        await fetch('/api/chat/mark-read', {
            method: 'POST'
        });
        updateUnreadCount();
    } catch (error) {
        console.error('Error marking messages as read:', error);
    }
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// Clean up on page unload
window.addEventListener('beforeunload', function () {
    if (pollInterval) {
        clearInterval(pollInterval);
    }
});
