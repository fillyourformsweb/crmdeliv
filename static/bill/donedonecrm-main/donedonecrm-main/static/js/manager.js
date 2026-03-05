document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const mobileSidebarToggle = document.getElementById('mobileSidebarToggle');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const logoutBtn = document.getElementById('logoutBtn');
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    const modalOverlay = document.getElementById('modalOverlay');
    
    // Modal elements
    const chatModal = document.getElementById('chatModal');
    const shareModal = document.getElementById('shareModal');
    const detailsModal = document.getElementById('detailsModal');
    
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
            assigned: "David Wilson",
            date: "2023-10-10",
            hoursOverdue: 36,
            dueAmount: "$1,200",
            reason: "Waiting for client feedback on design mockups"
        },
        {
            orderNo: "ORD-1002",
            name: "Sarah Johnson",
            service: "Mobile App",
            status: "Pending",
            assigned: "Emma Davis",
            date: "2023-10-09",
            hoursOverdue: 48,
            dueAmount: "$2,500",
            reason: "Development team waiting for API documentation"
        },
        {
            orderNo: "ORD-1005",
            name: "Alice Johnson",
            service: "Mobile App Development",
            status: "Pending",
            assigned: "Michael Brown",
            date: "2023-10-09",
            hoursOverdue: 48,
            dueAmount: "$3,500",
            reason: "Client hasn't provided required assets"
        },
        {
            orderNo: "ORD-1007",
            name: "Robert Chen",
            service: "CRM Implementation",
            status: "Hold",
            assigned: "Sophia Williams",
            date: "2023-10-08",
            hoursOverdue: 60,
            dueAmount: "$4,200",
            reason: "Budget approval pending from finance department"
        },
        {
            orderNo: "ORD-1008",
            name: "Robert Brown",
            service: "SEO Optimization",
            status: "Hold",
            assigned: "James Miller",
            date: "2023-10-08",
            hoursOverdue: 60,
            dueAmount: "$850",
            reason: "Technical issues with website hosting"
        },
        {
            orderNo: "ORD-1010",
            name: "Jennifer Taylor",
            service: "Brand Strategy",
            status: "In Progress",
            assigned: "Oliver Wilson",
            date: "2023-10-07",
            hoursOverdue: 72,
            dueAmount: "$3,800",
            reason: "Market research phase taking longer than expected"
        },
        {
            orderNo: "ORD-1011",
            name: "Thomas Anderson",
            service: "Cloud Migration",
            status: "Pending",
            assigned: "Emma Davis",
            date: "2023-10-06",
            hoursOverdue: 84,
            dueAmount: "$5,500",
            reason: "Waiting for security clearance from IT department"
        }
    ];
    
    const recentTasks = [
        {
            orderNo: "ORD-1015",
            name: "Emily Davis",
            service: "Logo Design",
            status: "Completed",
            assigned: "David Wilson",
            sharedWith: "Design Team",
            date: "2023-10-12",
            contact: "emily@example.com"
        },
        {
            orderNo: "ORD-1014",
            name: "Michael Wilson",
            service: "E-commerce Setup",
            status: "In Progress",
            assigned: "Sophia Williams",
            sharedWith: "Dev Team",
            date: "2023-10-11",
            contact: "michael@example.com"
        },
        {
            orderNo: "ORD-1013",
            name: "Sarah Miller",
            service: "Content Writing",
            status: "Pending",
            assigned: "James Miller",
            sharedWith: "Content Team",
            date: "2023-10-11",
            contact: "sarah@example.com"
        },
        {
            orderNo: "ORD-1012",
            name: "David Taylor",
            service: "Social Media Management",
            status: "In Progress",
            assigned: "Oliver Wilson",
            sharedWith: "Marketing Team",
            date: "2023-10-10",
            contact: "david@example.com"
        },
        {
            orderNo: "ORD-1009",
            name: "Jennifer Lee",
            service: "Brand Strategy",
            status: "Completed",
            assigned: "Emma Davis",
            sharedWith: "Strategy Team",
            date: "2023-10-09",
            contact: "jennifer@example.com"
        }
    ];
    
    // Populate overdue tasks table
    const overdueTable = document.getElementById('overdueTasksTable');
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
    
    // Populate recent tasks table
    const recentTable = document.getElementById('recentTasksTable');
    recentTasks.forEach(task => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${task.orderNo}</td>
            <td>${task.name}</td>
            <td>${task.service}</td>
            <td><span class="status-badge status-${task.status.toLowerCase().replace(' ', '')}">${task.status}</span></td>
            <td>${task.assigned}</td>
            <td>${task.sharedWith}</td>
            <td>${task.date}</td>
            <td><a href="mailto:${task.contact}" style="color: #2E8B57; text-decoration: none;">Contact</a></td>
            <td><button class="action-btn share" onclick="shareTaskModal('${task.orderNo}')">Share</button></td>
            <td><button class="action-btn details" onclick="viewTaskDetails('${task.orderNo}')">Details</button></td>
            <td><button class="action-btn chat" onclick="openChatModal('${task.orderNo}')">Chat</button></td>
        `;
        recentTable.appendChild(row);
    });
    
    // Update overdue badge
    document.getElementById('overdueBadge').textContent = overdueTasks.length;
    
    // Update stats counts
    document.getElementById('teamMembersCount').textContent = "8";
    document.getElementById('overdueTasksCount').textContent = overdueTasks.length;
    document.getElementById('activeTasksCount').textContent = "24";
    document.getElementById('completionRate').textContent = "78%";
    
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
    sidebarToggle.addEventListener('click', toggleSidebar);
    mobileSidebarToggle.addEventListener('click', openSidebar);
    sidebarOverlay.addEventListener('click', closeSidebar);
    
    // Logout button functionality
    logoutBtn.addEventListener('click', function(e) {
        e.preventDefault();
        if (confirm('Are you sure you want to logout?')) {
            showToast('Logged out successfully!', 'success');
            setTimeout(() => {
                // In a real app, you would redirect to login page
                // window.location.href = 'login.html';
                console.log('Redirecting to login page...');
            }, 1500);
        }
    });
    
    // View all tasks button functionality
    document.getElementById('viewAllTasks').addEventListener('click', function() {
        showToast('Redirecting to all tasks page...', 'info');
        // In a real app, you would redirect to tasks page
        // window.location.href = 'tasks.html';
    });
    
    // Navigation active state
    const currentPage = window.location.pathname.split('/').pop();
    document.querySelectorAll('.nav-links a').forEach(link => {
        const linkHref = link.getAttribute('href');
        if (linkHref === currentPage || (linkHref === 'manager.html' && currentPage === '')) {
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
        } else {
            toast.querySelector('i').className = 'fas fa-check-circle';
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
    
    // Export button functionality
    const exportBtn = document.querySelector('.btn-export');
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            showToast('Exporting data...', 'info');
            // Add export functionality here
        });
    }
    
    // Initialize modals
    initModals();
});

// Global functions for manager actions
let currentTaskOrderNo = '';
let currentTaskData = null;
let chatType = ''; // 'staff' or 'customer'

// Modal functions
function initModals() {
    const modalOverlay = document.getElementById('modalOverlay');
    
    // Close modals when clicking overlay
    modalOverlay.addEventListener('click', function() {
        closeAllModals();
    });
    
    // Close modals with escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    const modalOverlay = document.getElementById('modalOverlay');
    
    if (modal && modalOverlay) {
        modal.classList.add('active');
        modalOverlay.classList.add('active');
        document.body.style.overflow = 'hidden'; // Prevent scrolling
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    const modalOverlay = document.getElementById('modalOverlay');
    
    if (modal) {
        modal.classList.remove('active');
    }
    
    // Only remove overlay if no other modals are open
    const activeModals = document.querySelectorAll('.modal.active');
    if (activeModals.length === 0 && modalOverlay) {
        modalOverlay.classList.remove('active');
        document.body.style.overflow = ''; // Restore scrolling
    }
}

function closeAllModals() {
    const modals = document.querySelectorAll('.modal');
    const modalOverlay = document.getElementById('modalOverlay');
    
    modals.forEach(modal => {
        modal.classList.remove('active');
    });
    
    if (modalOverlay) {
        modalOverlay.classList.remove('active');
        document.body.style.overflow = ''; // Restore scrolling
    }
}

// Chat functionality
function openChatModal(orderNo) {
    currentTaskOrderNo = orderNo;
    const chatDetails = document.getElementById('chatDetails');
    const sendChatBtn = document.getElementById('sendChatBtn');
    
    // Reset chat options
    chatDetails.style.display = 'none';
    sendChatBtn.textContent = 'Next';
    sendChatBtn.onclick = function() {
        const chatDetailsDiv = document.getElementById('chatDetails');
        if (chatDetailsDiv.style.display === 'none') {
            // First click - show details
            chatDetailsDiv.style.display = 'block';
            this.textContent = 'Send Message';
        } else {
            // Second click - send message
            sendChatMessage();
        }
    };
    
    openModal('chatModal');
}

function startChat(type) {
    chatType = type;
    const chatDetails = document.getElementById('chatDetails');
    chatDetails.style.display = 'block';
    
    // Update recipient options based on chat type
    const recipientSelect = document.getElementById('chatRecipient');
    if (type === 'staff') {
        recipientSelect.innerHTML = `
            <option value="">Select staff member</option>
            <option value="david@company.com">David Wilson (Team Lead)</option>
            <option value="emma@company.com">Emma Davis (Designer)</option>
            <option value="michael@company.com">Michael Brown (Developer)</option>
            <option value="sophia@company.com">Sophia Williams (QA)</option>
            <option value="james@company.com">James Miller (Content)</option>
            <option value="oliver@company.com">Oliver Wilson (Marketing)</option>
        `;
    } else {
        // For customer chat, show customer options from recent tasks
        recipientSelect.innerHTML = `
            <option value="">Select customer</option>
            <option value="john@example.com">John Smith (ORD-1001)</option>
            <option value="sarah@example.com">Sarah Johnson (ORD-1002)</option>
            <option value="alice@example.com">Alice Johnson (ORD-1005)</option>
            <option value="robert@example.com">Robert Chen (ORD-1007)</option>
            <option value="jennifer@example.com">Jennifer Taylor (ORD-1010)</option>
            <option value="thomas@example.com">Thomas Anderson (ORD-1011)</option>
        `;
    }
}

function sendChatMessage() {
    const message = document.getElementById('chatMessage').value;
    const recipient = document.getElementById('chatRecipient').value;
    
    if (!message.trim()) {
        alert('Please enter a message');
        return;
    }
    
    if (!recipient) {
        alert('Please select a recipient');
        return;
    }
    
    console.log(`Sending chat message for task ${currentTaskOrderNo}:`, {
        type: chatType,
        recipient: recipient,
        message: message
    });
    
    showToast(`Message sent to ${recipient}`, 'success');
    closeModal('chatModal');
    
    // Reset form
    document.getElementById('chatMessage').value = '';
    document.getElementById('chatRecipient').value = '';
    document.getElementById('chatDetails').style.display = 'none';
}

// Share task functionality
function shareTaskModal(orderNo) {
    currentTaskOrderNo = orderNo;
    
    // Set task order number in modal
    document.getElementById('taskOrderNo').value = orderNo;
    
    // Clear previous selections
    const checkboxes = document.querySelectorAll('.staff-checklist input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    
    // Clear notes
    document.getElementById('shareMessage').value = '';
    
    openModal('shareModal');
}

function shareTask() {
    const taskOrderNo = document.getElementById('taskOrderNo').value;
    const notes = document.getElementById('shareMessage').value;
    
    // Get selected staff members
    const selectedStaff = [];
    const checkboxes = document.querySelectorAll('.staff-checklist input[type="checkbox"]:checked');
    checkboxes.forEach(checkbox => {
        selectedStaff.push(checkbox.value);
    });
    
    if (selectedStaff.length === 0) {
        alert('Please select at least one staff member to share with');
        return;
    }
    
    console.log(`Sharing task ${taskOrderNo}:`, {
        staff: selectedStaff,
        notes: notes
    });
    
    showToast(`Task ${taskOrderNo} shared with ${selectedStaff.length} staff member(s)`, 'success');
    closeModal('shareModal');
}

// Task details functionality
function viewTaskDetails(orderNo) {
    currentTaskOrderNo = orderNo;
    
    // Find task data
    let taskData = null;
    
    // Check in overdue tasks
    const overdueTask = [
        {
            orderNo: "ORD-1001",
            name: "John Smith",
            service: "Website Redesign",
            status: "In Progress",
            assigned: "David Wilson",
            date: "2023-10-10",
            hoursOverdue: 36,
            dueAmount: "$1,200",
            reason: "Waiting for client feedback on design mockups"
        },
        {
            orderNo: "ORD-1002",
            name: "Sarah Johnson",
            service: "Mobile App",
            status: "Pending",
            assigned: "Emma Davis",
            date: "2023-10-09",
            hoursOverdue: 48,
            dueAmount: "$2,500",
            reason: "Development team waiting for API documentation"
        },
        {
            orderNo: "ORD-1005",
            name: "Alice Johnson",
            service: "Mobile App Development",
            status: "Pending",
            assigned: "Michael Brown",
            date: "2023-10-09",
            hoursOverdue: 48,
            dueAmount: "$3,500",
            reason: "Client hasn't provided required assets"
        },
        {
            orderNo: "ORD-1007",
            name: "Robert Chen",
            service: "CRM Implementation",
            status: "Hold",
            assigned: "Sophia Williams",
            date: "2023-10-08",
            hoursOverdue: 60,
            dueAmount: "$4,200",
            reason: "Budget approval pending from finance department"
        },
        {
            orderNo: "ORD-1008",
            name: "Robert Brown",
            service: "SEO Optimization",
            status: "Hold",
            assigned: "James Miller",
            date: "2023-10-08",
            hoursOverdue: 60,
            dueAmount: "$850",
            reason: "Technical issues with website hosting"
        },
        {
            orderNo: "ORD-1010",
            name: "Jennifer Taylor",
            service: "Brand Strategy",
            status: "In Progress",
            assigned: "Oliver Wilson",
            date: "2023-10-07",
            hoursOverdue: 72,
            dueAmount: "$3,800",
            reason: "Market research phase taking longer than expected"
        },
        {
            orderNo: "ORD-1011",
            name: "Thomas Anderson",
            service: "Cloud Migration",
            status: "Pending",
            assigned: "Emma Davis",
            date: "2023-10-06",
            hoursOverdue: 84,
            dueAmount: "$5,500",
            reason: "Waiting for security clearance from IT department"
        }
    ].find(task => task.orderNo === orderNo);
    
    // Check in recent tasks
    const recentTask = [
        {
            orderNo: "ORD-1015",
            name: "Emily Davis",
            service: "Logo Design",
            status: "Completed",
            assigned: "David Wilson",
            date: "2023-10-12",
            hoursOverdue: 0,
            dueAmount: "$1,500",
            reason: "Successfully delivered to client"
        },
        {
            orderNo: "ORD-1014",
            name: "Michael Wilson",
            service: "E-commerce Setup",
            status: "In Progress",
            assigned: "Sophia Williams",
            date: "2023-10-11",
            hoursOverdue: 0,
            dueAmount: "$3,200",
            reason: "Payment processing integration in progress"
        },
        {
            orderNo: "ORD-1013",
            name: "Sarah Miller",
            service: "Content Writing",
            status: "Pending",
            assigned: "James Miller",
            date: "2023-10-11",
            hoursOverdue: 0,
            dueAmount: "$800",
            reason: "Awaiting client's brand guidelines"
        },
        {
            orderNo: "ORD-1012",
            name: "David Taylor",
            service: "Social Media Management",
            status: "In Progress",
            assigned: "Oliver Wilson",
            date: "2023-10-10",
            hoursOverdue: 0,
            dueAmount: "$1,200",
            reason: "Creating monthly content calendar"
        },
        {
            orderNo: "ORD-1009",
            name: "Jennifer Lee",
            service: "Brand Strategy",
            status: "Completed",
            assigned: "Emma Davis",
            date: "2023-10-09",
            hoursOverdue: 0,
            dueAmount: "$2,800",
            reason: "Final presentation delivered and approved"
        }
    ].find(task => task.orderNo === orderNo);
    
    taskData = overdueTask || recentTask;
    currentTaskData = taskData;
    
    if (!taskData) {
        alert('Task not found');
        return;
    }
    
    // Populate details in modal
    document.getElementById('detailOrderNo').textContent = taskData.orderNo;
    document.getElementById('detailCustomerName').textContent = taskData.name;
    document.getElementById('detailService').textContent = taskData.service;
    document.getElementById('detailStatus').textContent = taskData.status;
    document.getElementById('detailStatus').className = `status-badge status-${taskData.status.toLowerCase().replace(' ', '')}`;
    document.getElementById('detailAssignedTo').textContent = taskData.assigned;
    document.getElementById('detailDate').textContent = taskData.date;
    document.getElementById('detailHoursOverdue').textContent = taskData.hoursOverdue ? `${taskData.hoursOverdue} hrs` : '0 hrs';
    document.getElementById('detailDueAmount').textContent = taskData.dueAmount || 'N/A';
    document.getElementById('detailReason').innerHTML = `<p>${taskData.reason || 'No reason provided'}</p>`;
    
    // Reset update fields
    document.getElementById('updateStatus').value = '';
    document.getElementById('updateReason').value = '';
    
    openModal('detailsModal');
}

function updateTaskStatus() {
    const newStatus = document.getElementById('updateStatus').value;
    const reason = document.getElementById('updateReason').value;
    
    if (!newStatus) {
        alert('Please select a new status');
        return;
    }
    
    if (!reason.trim()) {
        alert('Please provide a reason for the status update');
        return;
    }
    
    console.log(`Updating task ${currentTaskOrderNo}:`, {
        oldStatus: currentTaskData.status,
        newStatus: newStatus,
        reason: reason
    });
    
    // Update the current task data
    currentTaskData.status = newStatus;
    currentTaskData.reason = reason;
    
    // In a real application, you would send this data to the server
    
    showToast(`Task ${currentTaskOrderNo} status updated to ${newStatus}`, 'success');
    closeModal('detailsModal');
    
    // Refresh the table (in a real app, you would reload data from server)
    setTimeout(() => {
        location.reload();
    }, 1000);
}

// Old function kept for backward compatibility
function assignTask(orderNo) {
    shareTaskModal(orderNo);
}