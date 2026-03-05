"""
Debug script to check if chat widget is properly loaded
Run this in browser console to diagnose chat button issues
"""

# Copy and paste this into browser console(F12):

console.log("=== CHAT WIDGET DEBUG ===");

# Check if elements exist
const chatButton = document.getElementById('chat-widget-button');
const chatWindow = document.getElementById('chat-widget-window');
const chatContainer = document.getElementById('chat-widget-container');

console.log("Chat container exists:", !!chatContainer);
console.log("Chat button exists:", !!chatButton);
console.log("Chat window exists:", !!chatWindow);

# Check if openChat function exists
console.log("window.openChat exists:", typeof window.openChat);

# Check if button is visible
if (chatButton) {
    const styles = window.getComputedStyle(chatButton);
    console.log("Button display:", styles.display);
    console.log("Button visibility:", styles.visibility);
    console.log("Button position:", styles.position);
}

# Try to manually trigger
if (typeof window.openChat === 'function') {
    console.log("Attempting to open chat...");
    window.openChat();
} else {
    console.error("window.openChat is not a function!");
}
