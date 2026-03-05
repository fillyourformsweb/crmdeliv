// Initialize user dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadUserApplications();
    loadNotifications();
    loadUserProfile();
});

// User profile functions
function loadUserProfile() {
    // In production, fetch from backend
    const userData = {
        name: "John Doe",
        email: "john@example.com",
        phone: "+91 9876543210",
        activeApps: 5,
        completedApps: 12
    };
    
    document.getElementById('userName').textContent = userData.name;
    document.getElementById('userEmail').textContent = userData.email;
    document.getElementById('activeApps').textContent = userData.activeApps;
    document.getElementById('completedApps').textContent = userData.completedApps;
}

// Application management
function loadUserApplications() {
    // Mock data - in production, fetch from backend
    const applications = [
        { id: 'APP-001', type: 'UPSC Application', date: '2024-01-15', status: 'Pending', action: 'Track' },
        { id: 'APP-002', type: 'SSC CGL', date: '2024-01-10', status: 'Approved', action: 'Download' },
        { id: 'APP-003', type: 'Company Registration', date: '2024-01-05', status: 'Completed', action: 'View' },
        { id: 'APP-004', type: 'GST Registration', date: '2024-01-02', status: 'Pending', action: 'Track' },
        { id: 'APP-005', type: 'Scholarship', date: '2023-12-28', status: 'Rejected', action: 'Revise' }
    ];
    
    const tableBody = document.getElementById('applicationsTable');
    tableBody.innerHTML = '';
    
    applications.forEach(app => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${app.id}</td>
            <td>${app.type}</td>
            <td>${app.date}</td>
            <td><span class="status-badge status-${app.status.toLowerCase()}">${app.status}</span></td>
            <td><button class="action-btn" onclick="handleApplicationAction('${app.id}')">${app.action}</button></td>
        `;
        tableBody.appendChild(row);
    });
}

function handleApplicationAction(appId) {
    alert(`Handling action for application ${appId}`);
    // In production, implement specific actions
}

function startNewApplication() {
    window.location.href = 'new-application.html';
}

function checkApplicationStatus() {
    const appId = prompt("Enter your Application ID:");
    if (appId) {
        alert(`Checking status for ${appId}...`);
        // In production, fetch status from backend
    }
}

function downloadCertificate() {
    alert("Downloading certificate...");
    // In production, generate and download certificate
}

function makePayment() {
    window.location.href = 'payment.html';
}

// Chat functionality
function sendStaffMessage() {
    const input = document.getElementById('staffChatInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    addStaffChatMessage(message, 'user');
    input.value = '';
    
    // Simulate staff response
    setTimeout(() => {
        addStaffChatMessage("Thank you for your message. Our support staff will get back to you soon.", 'staff');
    }, 2000);
}

function addStaffChatMessage(message, sender) {
    const messagesDiv = document.getElementById('staffChatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.innerHTML = `
        <p>${message}</p>
        <span class="time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
    `;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function attachFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.onchange = function(e) {
        const file = e.target.files[0];
        if (file) {
            addStaffChatMessage(`File attached: ${file.name}`, 'user');
        }
    };
    input.click();
}
// Initialize user dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadUserApplications();
    loadNotifications();
    loadUserProfile();
});

// User profile functions
function loadUserProfile() {
    // In production, fetch from backend
    const userData = {
        name: "John Doe",
        email: "john@example.com",
        phone: "+91 9876543210",
        activeApps: 5,
        completedApps: 12
    };
    
    document.getElementById('userName').textContent = userData.name;
    document.getElementById('userEmail').textContent = userData.email;
    document.getElementById('activeApps').textContent = userData.activeApps;
    document.getElementById('completedApps').textContent = userData.completedApps;
}

// Application management
function loadUserApplications() {
    // Mock data - in production, fetch from backend
    const applications = [
        { id: 'APP-001', type: 'UPSC Application', date: '2024-01-15', status: 'Pending', action: 'Track' },
        { id: 'APP-002', type: 'SSC CGL', date: '2024-01-10', status: 'Approved', action: 'Download' },
        { id: 'APP-003', type: 'Company Registration', date: '2024-01-05', status: 'Completed', action: 'View' },
        { id: 'APP-004', type: 'GST Registration', date: '2024-01-02', status: 'Pending', action: 'Track' },
        { id: 'APP-005', type: 'Scholarship', date: '2023-12-28', status: 'Rejected', action: 'Revise' }
    ];
    
    const tableBody = document.getElementById('applicationsTable');
    tableBody.innerHTML = '';
    
    applications.forEach(app => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${app.id}</td>
            <td>${app.type}</td>
            <td>${app.date}</td>
            <td><span class="status-badge status-${app.status.toLowerCase()}">${app.status}</span></td>
            <td><button class="action-btn" onclick="handleApplicationAction('${app.id}')">${app.action}</button></td>
        `;
        tableBody.appendChild(row);
    });
}

function handleApplicationAction(appId) {
    alert(`Handling action for application ${appId}`);
    // In production, implement specific actions
}

function startNewApplication() {
    window.location.href = 'new-application.html';
}

function checkApplicationStatus() {
    const appId = prompt("Enter your Application ID:");
    if (appId) {
        alert(`Checking status for ${appId}...`);
        // In production, fetch status from backend
    }
}

function downloadCertificate() {
    alert("Downloading certificate...");
    // In production, generate and download certificate
}

function makePayment() {
    window.location.href = 'payment.html';
}

// Chat functionality
function sendStaffMessage() {
    const input = document.getElementById('staffChatInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    addStaffChatMessage(message, 'user');
    input.value = '';
    
    // Simulate staff response
    setTimeout(() => {
        addStaffChatMessage("Thank you for your message. Our support staff will get back to you soon.", 'staff');
    }, 2000);
}

function addStaffChatMessage(message, sender) {
    const messagesDiv = document.getElementById('staffChatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.innerHTML = `
        <p>${message}</p>
        <span class="time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
    `;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function attachFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.onchange = function(e) {
        const file = e.target.files[0];
        if (file) {
            addStaffChatMessage(`File attached: ${file.name}`, 'user');
        }
    };
    input.click();
}

// Notifications
function loadNotifications() {
    const notifications = [
        { id: 1, type: 'payment', message: 'Payment for APP-001 received', time: '2 hours ago', read: false },
        { id: 2, type: 'status', message: 'APP-002 approved successfully', time: '1 day ago', read: true },
        { id: 3, type: 'alert', message: 'Document verification required for APP-004', time: '2 days ago', read: false },
        { id: 4, type: 'update', message: 'New service available: Online Verification', time: '3 days ago', read: true }
    ];
    
    const notificationsList = document.getElementById('notificationsList');
    notificationsList.innerHTML = '';
    
    notifications.forEach(notif => {
        const notifDiv = document.createElement('div');
        notifDiv.className = `notification-item ${notif.read ? '' : 'unread'}`;
        notifDiv.innerHTML = `
            <div class="notification-icon">
                <i class="fas fa-${getNotificationIcon(notif.type)}"></i>
            </div>
            <div class="notification-content">
                <p>${notif.message}</p>
                <small>${notif.time}</small>
            </div>
        `;
        notificationsList.appendChild(notifDiv);
    });
}

function getNotificationIcon(type) {
    const icons = {
        'payment': 'credit-card',
        'status': 'check-circle',
        'alert': 'exclamation-circle',
        'update': 'bell'
    };
    return icons[type] || 'bell';
}

// User chatbot
function toggleUserChatbot() {
    const chatbotWindow = document.getElementById('userChatbotWindow');
    chatbotWindow.classList.toggle('show');
}

function sendUserChatbotMessage() {
    const input = document.getElementById('userChatbotInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    addUserChatbotMessage(message, 'user');
    input.value = '';
    
    setTimeout(() => {
        const response = generateUserChatbotResponse(message);
        addUserChatbotMessage(response, 'bot');
    }, 1000);
}

function addUserChatbotMessage(message, sender) {
    const messagesDiv = document.getElementById('userChatbotMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.innerHTML = `<p>${message}</p>`;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function generateUserChatbotResponse(message) {
    const lowerMessage = message.toLowerCase();
    
    if (lowerMessage.includes('application status')) {
        return "To check your application status:<br>1. Go to 'My Applications'<br>2. Find your application ID<br>3. Click on 'Track' button<br>Or enter your application ID and I'll check for you.";
    }
    
    if (lowerMessage.includes('payment') || lowerMessage.includes('fee')) {
        return "Payment options:<br>1. Online Payment (Credit/Debit Card)<br>2. UPI<br>3. Net Banking<br>4. Cash at our office<br>You can make payment from the 'Make Payment' button in your dashboard.";
    }
    
    if (lowerMessage.includes('document') || lowerMessage.includes('upload')) {
        return "To upload documents:<br>1. Go to your application<br>2. Click 'Upload Documents'<br>3. Select files<br>4. Submit<br>Maximum file size: 5MB per file. Supported formats: PDF, JPG, PNG.";
    }
    
    return "I can help you with:<br>- Application status<br>- Payment queries<br>- Document uploads<br>- Service information<br>Please ask a specific question about your applications.";
}
// Notifications
function loadNotifications() {
    const notifications = [
        { id: 1, type: 'payment', message: 'Payment for APP-001 received', time: '2 hours ago', read: false },
        { id: 2, type: 'status', message: 'APP-002 approved successfully', time: '1 day ago', read: true },
        { id: 3, type: 'alert', message: 'Document verification required for APP-004', time: '2 days ago', read: false },
        { id: 4, type: 'update', message: 'New service available: Online Verification', time: '3 days ago', read: true }
    ];
    
    const notificationsList = document.getElementById('notificationsList');
    notificationsList.innerHTML = '';
    
    notifications.forEach(notif => {
        const notifDiv = document.createElement('div');
        notifDiv.className = `notification-item ${notif.read ? '' : 'unread'}`;
        notifDiv.innerHTML = `
            <div class="notification-icon">
                <i class="fas fa-${getNotificationIcon(notif.type)}"></i>
            </div>
            <div class="notification-content">
                <p>${notif.message}</p>
                <small>${notif.time}</small>
            </div>
        `;
        notificationsList.appendChild(notifDiv);
    });
}

function getNotificationIcon(type) {
    const icons = {
        'payment': 'credit-card',
        'status': 'check-circle',
        'alert': 'exclamation-circle',
        'update': 'bell'
    };
    return icons[type] || 'bell';
}

// User chatbot
function toggleUserChatbot() {
    const chatbotWindow = document.getElementById('userChatbotWindow');
    chatbotWindow.classList.toggle('show');
}

function sendUserChatbotMessage() {
    const input = document.getElementById('userChatbotInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    addUserChatbotMessage(message, 'user');
    input.value = '';
    
    setTimeout(() => {
        const response = generateUserChatbotResponse(message);
        addUserChatbotMessage(response, 'bot');
    }, 1000);
}

function addUserChatbotMessage(message, sender) {
    const messagesDiv = document.getElementById('userChatbotMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.innerHTML = `<p>${message}</p>`;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function generateUserChatbotResponse(message) {
    const lowerMessage = message.toLowerCase();
    
    if (lowerMessage.includes('application status')) {
        return "To check your application status:<br>1. Go to 'My Applications'<br>2. Find your application ID<br>3. Click on 'Track' button<br>Or enter your application ID and I'll check for you.";
    }
    
    if (lowerMessage.includes('payment') || lowerMessage.includes('fee')) {
        return "Payment options:<br>1. Online Payment (Credit/Debit Card)<br>2. UPI<br>3. Net Banking<br>4. Cash at our office<br>You can make payment from the 'Make Payment' button in your dashboard.";
    }
    
    if (lowerMessage.includes('document') || lowerMessage.includes('upload')) {
        return "To upload documents:<br>1. Go to your application<br>2. Click 'Upload Documents'<br>3. Select files<br>4. Submit<br>Maximum file size: 5MB per file. Supported formats: PDF, JPG, PNG.";
    }
    
    return "I can help you with:<br>- Application status<br>- Payment queries<br>- Document uploads<br>- Service information<br>Please ask a specific question about your applications.";
}