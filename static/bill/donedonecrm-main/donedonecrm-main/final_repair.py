import os
import re

def fix_task_html():
    path = 'd:/deleviry-crm420-main/deleviry-crm420-main/static/bill/donedonecrm-main/donedonecrm-main/templates/task.html'
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
        
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Remove any existing definitions of toggleBillDropdown and closeBillDropdown
    # This is a bit tricky with regex for multi-line, but we can target the known broken versions
    content = re.sub(r'function toggleBillDropdown\(taskId\) \{.*?\}\s*\}', '', content, flags=re.DOTALL)
    content = re.sub(r'function closeBillDropdown\(taskId\) \{.*?\}\s*\}', '', content, flags=re.DOTALL)
    
    # Also remove any redundant window exports
    content = content.replace('window.toggleBillDropdown = toggleBillDropdown;', '')
    content = content.replace('window.closeBillDropdown = closeBillDropdown;', '')
    
    # 2. Insert fresh definitions at the top of the main script block
    functions_logic = """
        function toggleBillDropdown(taskId) {
            const dropdown = document.getElementById(`billDropdown${taskId}`);
            if (dropdown) {
                dropdown.classList.toggle('show');
                document.querySelectorAll('.bill-dropdown-content').forEach(d => {
                    if (d.id !== `billDropdown${taskId}`) d.classList.remove('show');
                });
            }
        }
        function closeBillDropdown(taskId) {
            const dropdown = document.getElementById(`billDropdown${taskId}`);
            if (dropdown) dropdown.classList.remove('show');
        }
        window.toggleBillDropdown = toggleBillDropdown;
        window.closeBillDropdown = closeBillDropdown;
"""
    
    # Insert after <script>
    content = content.replace('<script>', '<script>\n' + functions_logic)
    
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)
    print("Repaired task.html")

def fix_chat_widget_html():
    path = 'd:/deleviry-crm420-main/deleviry-crm420-main/static/bill/donedonecrm-main/donedonecrm-main/templates/chat_widget.html'
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    # We'll overwrite with a clean, verified version to eliminate all corrupted bits
    clean_script = """
<script>
    (function () {
        const chatButton = document.getElementById('chat-widget-button');
        const chatWindow = document.getElementById('chat-widget-window');
        const closeButton = document.getElementById('chat-close-button');
        const messageInput = document.getElementById('chat-message-input');
        const sendButton = document.getElementById('chat-send-button');
        const messagesContainer = document.getElementById('chat-messages-container');
        const fileInput = document.getElementById('chat-file-input');
        const filePreview = document.getElementById('chat-file-preview');
        const fileNamePreview = document.getElementById('file-name-preview');
        const removeFileButton = document.getElementById('remove-file-button');
        const fullscreenBtn = document.getElementById('chat-fullscreen-button');

        let lastMessageId = 0;
        let isWindowOpen = false;
        let isFullscreen = false;
        let pollInterval;

        function scrollToBottom() {
            if (messagesContainer) {
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }

        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', () => {
                isFullscreen = !isFullscreen;
                chatWindow.classList.toggle('fullscreen');
                if (isFullscreen) {
                    fullscreenBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" /></svg>';
                } else {
                    fullscreenBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" /></svg>';
                }
                scrollToBottom();
            });
        }

        chatButton.addEventListener('click', () => {
            isWindowOpen = !isWindowOpen;
            chatWindow.classList.toggle('hidden');
            if (isWindowOpen) {
                fetchMessages();
                startPolling();
                messageInput.focus();
                const badge = document.getElementById('chat-notification-badge');
                if (badge) badge.classList.add('hidden');
            } else {
                stopPolling();
            }
        });

        if (closeButton) {
            closeButton.addEventListener('click', () => {
                isWindowOpen = false;
                chatWindow.classList.add('hidden');
                stopPolling();
            });
        }

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                fileNamePreview.textContent = e.target.files[0].name;
                filePreview.classList.remove('hidden');
            }
        });

        removeFileButton.addEventListener('click', () => {
            fileInput.value = '';
            filePreview.classList.add('hidden');
        });

        async function sendMessage() {
            const message = messageInput.value.trim();
            const file = fileInput.files[0];
            if (!message && !file) return;

            const formData = new FormData();
            if (message) formData.append('message', message);
            if (file) formData.append('file', file);

            messageInput.value = '';
            fileInput.value = '';
            filePreview.classList.add('hidden');

            try {
                const response = await fetch('/api/chat/send', { method: 'POST', body: formData });
                const result = await response.json();
                if (result.status === 'success') {
                    fetchMessages();
                } else {
                    alert('Error sending message: ' + (result.error || 'Unknown error'));
                }
            } catch (error) {
                console.error('Error sending message:', error);
            }
        }

        sendButton.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });

        async function fetchMessages() {
            try {
                const response = await fetch('/api/chat/messages?limit=50');
                const data = await response.json();
                if (data.messages) renderMessages(data.messages);
            } catch (error) { console.error('Error fetching messages:', error); }
        }

        function renderMessages(messages) {
            const currentUserId = {{ session.get('user_id', 0) }};
            const shouldScroll = messagesContainer.scrollTop + messagesContainer.clientHeight >= messagesContainer.scrollHeight - 50;
            messagesContainer.innerHTML = '';

            if (messages.length === 0) {
                messagesContainer.innerHTML = '<div style="text-align:center;color:#999;margin-top:20px;font-size:0.8rem;">No messages yet. Say hi!</div>';
                return;
            }

            messages.forEach(msg => {
                const isMine = msg.sender_id === currentUserId;
                const msgDiv = document.createElement('div');
                msgDiv.className = "message " + (isMine ? 'message-sent' : 'message-received');

                let content = '';
                if (!isMine) content += '<div class="sender-info">' + msg.sender_name + ' (' + msg.sender_role + ')</div>';
                if (msg.message) content += '<div class="message-text">' + msg.message + '</div>';
                if (msg.file_path) {
                    if (msg.file_type === 'image') {
                        content += '<img src="' + msg.file_path + '" class="attachment-image" onclick="window.open(this.src)">';
                    } else {
                        content += '<a href="' + msg.file_path + '" target="_blank" class="file-attachment"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg><span>' + (msg.file_name || 'Download File') + '</span></a>';
                    }
                }
                const date = new Date(msg.timestamp);
                const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                content += '<div class="message-time">' + timeStr + '</div>';
                msgDiv.innerHTML = content;
                messagesContainer.appendChild(msgDiv);
            });

            if (shouldScroll || lastMessageId === 0) scrollToBottom();
            if (messages.length > 0) lastMessageId = messages[messages.length - 1].id;
        }

        function startPolling() { stopPolling(); pollInterval = setInterval(fetchMessages, 3000); }
        function stopPolling() { if (pollInterval) clearInterval(pollInterval); }

        window.openChat = function () { if (!isWindowOpen) chatButton.click(); };

        function showBrowserNotification(msg) {
            if (!("Notification" in window) || Notification.permission !== "granted") return;
            const notification = new Notification('New message from ' + msg.sender_name, {
                body: msg.message || "Sent a file",
                icon: "/static/favicon.ico"
            });
            notification.onclick = function () { window.focus(); window.openChat(); };
        }

        if ("Notification" in window && Notification.permission !== "granted" && Notification.permission !== "denied") {
            Notification.requestPermission();
        }

        setInterval(async () => {
            if (isWindowOpen) return;
            try {
                const response = await fetch('/api/chat/messages?limit=1');
                const data = await response.json();
                if (data.messages && data.messages.length > 0) {
                    const latestMsg = data.messages[0];
                    if (lastMessageId !== 0 && latestMsg.id > lastMessageId) {
                        const badge = document.getElementById('chat-notification-badge');
                        if (badge) badge.classList.remove('hidden');
                        showBrowserNotification(latestMsg);
                    }
                    if (lastMessageId === 0) lastMessageId = latestMsg.id;
                }
            } catch (e) { }
        }, 10000);
    })();
</script>
"""
    with open(path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Replace the existing script tag with the clean one
    new_html = re.sub(r'<script>.*?</script>', clean_script, html_content, flags=re.DOTALL)
    
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(new_html)
    print("Repaired chat_widget.html")

if __name__ == "__main__":
    fix_task_html()
    fix_chat_widget_html()
