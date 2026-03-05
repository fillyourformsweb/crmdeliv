
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const mobileSidebarToggle = document.getElementById('mobileSidebarToggle');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const mainContent = document.getElementById('mainContent');
    const logoutBtn = document.getElementById('logoutBtn');
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    
    // Chat specific elements
    const checkoutBtn = document.getElementById('checkoutBtn');
    const checkoutModal = document.getElementById('checkoutModal');
    const quickRepliesModal = document.getElementById('quickRepliesModal');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatMessages = document.getElementById('chatMessages');
    
    // Set current date in footer
    const currentDate = new Date();
    const dateString = currentDate.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
    document.getElementById('currentDate').textContent = dateString;
    
    // Initialize sidebar state
    let isSidebarOpen = true;
    
    // Check screen width on load
    if (window.innerWidth <= 768) {
        closeSidebar();
    }
    
    // Sample data for tasks
    const overdueTasks = [
        {
            orderNo: "ORD-1001",
            name: "John Smith",
            service: "Website Redesign",
            status: "In Progress",
            assigned: "You",
            date: "2023-10-10",
            hoursOverdue: 36,
            dueAmount: "$1,200"
        },
        {
            orderNo: "ORD-1005",
            name: "Alice Johnson",
            service: "Mobile App Development",
            status: "Pending",
            assigned: "You",
            date: "2023-10-09",
            hoursOverdue: 48,
            dueAmount: "$3,500"
        },
        {
            orderNo: "ORD-1008",
            name: "Robert Brown",
            service: "SEO Optimization",
            status: "Hold",
            assigned: "You",
            date: "2023-10-08",
            hoursOverdue: 60,
            dueAmount: "$850"
        }
    ];
    
    const recentTasks = [
        {
            orderNo: "ORD-1012",
            name: "Emily Davis",
            service: "Logo Design",
            status: "Completed",
            assigned: "You",
            sharedWith: "Design Team",
            date: "2023-10-12",
            contact: "emily@example.com"
        },
        {
            orderNo: "ORD-1011",
            name: "Michael Wilson",
            service: "E-commerce Setup",
            status: "In Progress",
            assigned: "You",
            sharedWith: "Dev Team",
            date: "2023-10-11",
            contact: "michael@example.com"
        },
        {
            orderNo: "ORD-1010",
            name: "Sarah Miller",
            service: "Content Writing",
            status: "Pending",
            assigned: "You",
            sharedWith: "Content Team",
            date: "2023-10-11",
            contact: "sarah@example.com"
        },
        {
            orderNo: "ORD-1009",
            name: "David Taylor",
            service: "Social Media Management",
            status: "In Progress",
            assigned: "You",
            sharedWith: "Marketing Team",
            date: "2023-10-10",
            contact: "david@example.com"
        },
        {
            orderNo: "ORD-1007",
            name: "Jennifer Lee",
            service: "Brand Strategy",
            status: "Completed",
            assigned: "You",
            sharedWith: "Strategy Team",
            date: "2023-10-09",
            contact: "jennifer@example.com"
        }
    ];
    
    // Sample chat messages
    const chatMessagesData = [
        {
            id: 1,
            sender: "customer",
            content: "Hello! Can you give me an update on my website redesign?",
            time: "10:15 AM",
            date: "Today"
        },
        {
            id: 2,
            sender: "staff",
            content: "Hi John! Yes, I'm currently working on the homepage design. Should have the mockup ready by this afternoon.",
            time: "10:20 AM",
            date: "Today"
        },
        {
            id: 3,
            sender: "customer",
            content: "Great! Can you make sure the color scheme matches our brand guidelines?",
            time: "10:25 AM",
            date: "Today"
        },
        {
            id: 4,
            sender: "staff",
            content: "Absolutely! I'm using the exact hex codes from your brand guide. I'll send you a preview before finalizing.",
            time: "10:28 AM",
            date: "Today"
        },
        {
            id: 5,
            sender: "customer",
            content: "Perfect! When do you think the whole project will be completed?",
            time: "10:30 AM",
            date: "Today"
        }
    ];
    
    // Populate overdue tasks table
    const overdueTable = document.getElementById('overdueTasksTable');
    if (overdueTable) {
        overdueTasks.forEach(task => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${task.orderNo}</td>
                <td>${task.name}</td>
                <td>${task.service}</td>
                <td><span class="status-badge status-${task.status.toLowerCase().replace(' ', '')}">${task.status}</span></td>
                <td>${task.assigned}</td>
                <td>${task.date}</td>
                <td><span style="color: #E74C3C; font-weight: 600;">${task.hoursOverdue} hrs</span></td>
                <td>${task.dueAmount}</td>
                <td><button class="action-btn share" onclick="shareTaskModal('${task.orderNo}')">Share</button></td>
                <td><button class="action-btn details" onclick="viewTaskDetails('${task.orderNo}')">Details</button></td>
                <td><button class="action-btn chat" onclick="openChatModal('${task.orderNo}')">Chat</button></td>
            `;
            overdueTable.appendChild(row);
        });
    }
    
    // Populate recent tasks table
    const recentTable = document.getElementById('recentTasksTable');
    if (recentTable) {
        recentTasks.forEach(task => {
            const row = document.createElement('tr');
            row.innerHTML = `
                  <td>${task.orderNo}</td>
                <td>${task.name}</td>
                <td>${task.service}</td>
                <td><span class="status-badge status-${task.status.toLowerCase().replace(' ', '')}">${task.status}</span></td>
                <td>${task.assigned}</td>
                <td>${task.date}</td>
                <td><span style="color: #E74C3C; font-weight: 600;">${task.hoursOverdue} hrs</span></td>
                <td>${task.dueAmount}</td>
                <td><button class="action-btn share" onclick="shareTaskModal('${task.orderNo}')">Share</button></td>
                <td><button class="action-btn details" onclick="viewTaskDetails('${task.orderNo}')">Details</button></td>
                <td><button class="action-btn chat" onclick="openChatModal('${task.orderNo}')">Chat</button></td>
            `;
            recentTable.appendChild(row);
        });
    }
    
    // Load chat messages if on chat page
    if (chatMessages) {
        loadChatMessages();
        setupChatEventListeners();
        setupCheckoutModal();
    }
    
    // Update overdue badge
    const overdueBadge = document.getElementById('overdueBadge');
    if (overdueBadge) {
        overdueBadge.textContent = overdueTasks.length;
    }
    
    // Update stats counts
    const todayTasksCount = document.getElementById('todayTasksCount');
    const overdueTasksCount = document.getElementById('overdueTasksCount');
    const totalTasksCount = document.getElementById('totalTasksCount');
    const completedTasksCount = document.getElementById('completedTasksCount');
    
    if (todayTasksCount) todayTasksCount.textContent = "12";
    if (overdueTasksCount) overdueTasksCount.textContent = overdueTasks.length;
    if (totalTasksCount) totalTasksCount.textContent = "47";
    if (completedTasksCount) completedTasksCount.textContent = "32";
    
    // Sidebar Functions
    function toggleSidebar() {
        if (isSidebarOpen) {
            closeSidebar();
        } else {
            openSidebar();
        }
    }
    
    function openSidebar() {
        sidebar.classList.remove('hidden');
        sidebarOverlay.classList.add('active');
        isSidebarOpen = true;
    }
    
    function closeSidebar() {
        sidebar.classList.add('hidden');
        sidebarOverlay.classList.remove('active');
        isSidebarOpen = false;
    }
    
    // Event Listeners for Sidebar
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }
    if (mobileSidebarToggle) {
        mobileSidebarToggle.addEventListener('click', openSidebar);
    }
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeSidebar);
    }
    
    // Logout button functionality
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (confirm('Are you sure you want to logout?')) {
                showToast('Logged out successfully!', 'success');
                setTimeout(() => {
                    // In a real app, you would redirect to login page
                    window.location.href = 'login.html';
                }, 1500);
            }
        });
    }
    
    // View all tasks button functionality
    const viewAllTasksBtn = document.getElementById('viewAllTasks');
    if (viewAllTasksBtn) {
        viewAllTasksBtn.addEventListener('click', function() {
            showToast('Redirecting to all tasks page...', 'info');
            window.location.href = 'tasks.html';
        });
    }
    
    // Quick links functionality
    document.querySelectorAll('.quick-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const linkText = this.textContent.trim();
            const href = this.getAttribute('href');
            showToast(`Navigating to ${linkText}...`, 'info');
            window.location.href = href;
        });
    });
    
    // Navigation active state
    const currentPage = window.location.pathname.split('/').pop();
    document.querySelectorAll('.nav-links a').forEach(link => {
        const linkHref = link.getAttribute('href');
        if (linkHref === currentPage || (linkHref === 'staff.html' && currentPage === '')) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth <= 768) {
            if (isSidebarOpen) {
                closeSidebar();
            }
        } else {
            if (!isSidebarOpen) {
                openSidebar();
            }
        }
    });
    
    // Toast notification function
    function showToast(message, type = 'success') {
        if (!toast || !toastMessage) return;
        
        toastMessage.textContent = message;
        toast.className = 'toast';
        
        // Add type class
        if (type === 'error') {
            toast.classList.add('error');
            toast.querySelector('i').className = 'fas fa-exclamation-circle';
        } else if (type === 'warning') {
            toast.classList.add('warning');
            toast.querySelector('i').className = 'fas fa-exclamation-triangle';
        } else if (type === 'info') {
            toast.querySelector('i').className = 'fas fa-info-circle';
        }
        
        // Show toast
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        // Hide toast after 3 seconds
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
    
    // Chat Functions
    function loadChatMessages() {
        chatMessages.innerHTML = '';
        chatMessagesData.forEach(msg => {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${msg.sender === 'staff' ? 'sent' : 'received'}`;
            messageDiv.innerHTML = `
                <div class="message-header">
                    <span>${msg.sender === 'staff' ? 'You' : 'Customer'}</span>
                    <span class="message-time">${msg.time} • ${msg.date}</span>
                </div>
                <div class="message-content">${msg.content}</div>
            `;
            chatMessages.appendChild(messageDiv);
        });
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function setupChatEventListeners() {
        // Send message
        sendBtn.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Quick replies button
        const quickReplyBtn = document.getElementById('quickReplyBtn');
        if (quickReplyBtn) {
            quickReplyBtn.addEventListener('click', function() {
                showModal('quickRepliesModal');
            });
        }
        
        // Quick reply buttons
        document.querySelectorAll('.quick-reply-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const reply = this.getAttribute('data-reply');
                messageInput.value = reply;
                closeModal('quickRepliesModal');
            });
        });
        
        // Conversation items
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.addEventListener('click', function() {
                document.querySelectorAll('.conversation-item').forEach(i => i.classList.remove('active'));
                this.classList.add('active');
                const orderNo = this.getAttribute('data-order');
                switchConversation(orderNo);
            });
        });
    }
    
    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;
        
        // Add message to chat
        const currentTime = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message sent';
        messageDiv.innerHTML = `
            <div class="message-header">
                <span>You</span>
                <span class="message-time">${currentTime} • Today</span>
            </div>
            <div class="message-content">${message}</div>
        `;
        chatMessages.appendChild(messageDiv);
        
        // Clear input
        messageInput.value = '';
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Simulate customer reply after 2 seconds
        setTimeout(simulateCustomerReply, 2000);
    }
    
    function simulateCustomerReply() {
        const replies = [
            "Thanks for the update!",
            "That sounds good, looking forward to seeing it.",
            "Can you please share the progress so far?",
            "When can I expect the next update?",
            "Perfect, thank you for your hard work!"
        ];
        const randomReply = replies[Math.floor(Math.random() * replies.length)];
        const currentTime = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message received';
        messageDiv.innerHTML = `
            <div class="message-header">
                <span>Customer</span>
                <span class="message-time">${currentTime} • Today</span>
            </div>
            <div class="message-content">${randomReply}</div>
        `;
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Update unread badge
        const unreadBadge = document.querySelector('.unread-badge');
        if (unreadBadge) {
            const currentCount = parseInt(unreadBadge.textContent) || 0;
            unreadBadge.textContent = currentCount + 1;
        }
    }
    
    function switchConversation(orderNo) {
        showToast(`Switched to conversation for ${orderNo}`, 'info');
        // In a real app, you would load conversation history from server
        loadChatMessages();
    }
    
    // Checkout Modal Functions
    function setupCheckoutModal() {
        if (!checkoutBtn) return;
        
        checkoutBtn.addEventListener('click', function() {
            showModal('checkoutModal');
        });
        
        // File upload
        const fileUploadArea = document.getElementById('fileUploadArea');
        const deliveryFiles = document.getElementById('deliveryFiles');
        const fileList = document.getElementById('fileList');
        
        if (fileUploadArea && deliveryFiles) {
            fileUploadArea.addEventListener('click', () => deliveryFiles.click());
            
            deliveryFiles.addEventListener('change', function(e) {
                fileList.innerHTML = '';
                Array.from(e.target.files).forEach(file => {
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';
                    fileItem.innerHTML = `
                        <span>${file.name}</span>
                        <button onclick="this.parentElement.remove()">Remove</button>
                    `;
                    fileList.appendChild(fileItem);
                });
            });
        }
        
        // Modal close buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', function() {
                const modal = this.closest('.modal');
                if (modal) {
                    closeModal(modal.id);
                }
            });
        });
        
        // Cancel checkout
        const cancelCheckout = document.getElementById('cancelCheckout');
        if (cancelCheckout) {
            cancelCheckout.addEventListener('click', function() {
                closeModal('checkoutModal');
            });
        }
        
        // Confirm checkout
        const confirmCheckout = document.getElementById('confirmCheckout');
        if (confirmCheckout) {
            confirmCheckout.addEventListener('click', function() {
                const completionNotes = document.getElementById('completionNotes').value;
                const sendInvoice = document.getElementById('sendInvoice').checked;
                const requestFeedback = document.getElementById('requestFeedback').checked;
                
                if (!completionNotes.trim()) {
                    showToast('Please add completion notes', 'error');
                    return;
                }
                
                // Simulate checkout process
                showToast('Processing order completion...', 'info');
                
                setTimeout(() => {
                    closeModal('checkoutModal');
                    showToast('Order marked as completed successfully! Invoice sent to customer.', 'success');
                    
                    // Update status in UI
                    const statusBadge = document.querySelector('.status-text');
                    if (statusBadge) {
                        statusBadge.textContent = 'Completed';
                        statusBadge.className = 'status-text status-completed';
                    }
                    
                    // Update checkout button
                    checkoutBtn.innerHTML = '<i class="fas fa-check"></i> Completed';
                    checkoutBtn.style.background = '#28a745';
                    checkoutBtn.disabled = true;
                    
                    // Update overdue text
                    const overdueText = document.querySelector('.overdue-text');
                    if (overdueText) {
                        overdueText.textContent = '0 hrs';
                        overdueText.style.color = '#28a745';
                    }
                }, 2000);
            });
        }
    }
    
    function showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
        }
    }
    
    function closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
        }
    }
    
    // Global functions for task actions
    window.shareTaskModal = function(orderNo) {
        showToast(`Sharing task ${orderNo}...`, 'info');
        // Implement share functionality
    };
    
    window.viewTaskDetails = function(orderNo) {
        showToast(`Viewing details for ${orderNo}...`, 'info');
        // Implement view details functionality
    };
    
    window.openChatModal = function(orderNo) {
        showToast(`Opening chat for ${orderNo}...`, 'info');
        // Redirect to chat portal with specific order
        window.location.href = `staffchat.html?order=${orderNo}`;
    };
    
    // Export button functionality
    const exportBtn = document.querySelector('.btn-export');
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            showToast('Exporting data...', 'info');
            // Add export functionality here
        });
    }
});
