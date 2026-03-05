// Task Management JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize task management system
    initTaskManagement();
});

function initTaskManagement() {
    // Initialize event listeners
    initEventListeners();
    
    // Load initial data
    loadServices();
    loadStaffMembers();
    loadTasks();
}

function initEventListeners() {
    // Add task button
    const addTaskBtn = document.getElementById('addTaskBtn');
    if (addTaskBtn) {
        addTaskBtn.addEventListener('click', showTaskForm);
    }

    // Cancel task button
    const cancelTaskBtn = document.getElementById('cancelTaskBtn');
    if (cancelTaskBtn) {
        cancelTaskBtn.addEventListener('click', hideTaskForm);
    }

    // Task form submission
    const taskForm = document.getElementById('taskForm');
    if (taskForm) {
        taskForm.addEventListener('submit', handleTaskSubmit);
    }

    // Contact number auto-suggest
    const contactInput = document.getElementById('contactNumber');
    if (contactInput) {
        contactInput.addEventListener('input', debounce(loadCustomerSuggestions, 300));
    }

    // Search functionality
    const taskSearch = document.getElementById('taskSearch');
    if (taskSearch) {
        taskSearch.addEventListener('input', debounce(searchTasks, 300));
    }

    // Payment modal
    const confirmPaymentBtn = document.getElementById('confirmPayment');
    if (confirmPaymentBtn) {
        confirmPaymentBtn.addEventListener('click', completeTaskWithPayment);
    }

    // Initialize customer name from contact number
    if (contactInput) {
        contactInput.addEventListener('blur', function() {
            if (this.value.length >= 10) {
                autoFillCustomerName(this.value);
            }
        });
    }
}

async function loadServices() {
    try {
        const response = await fetch('/api/services');
        const services = await response.json();
        
        const serviceSelect = document.getElementById('serviceType');
        if (serviceSelect) {
            serviceSelect.innerHTML = '<option value="">Select Service</option>';
            services.forEach(service => {
                const option = document.createElement('option');
                option.value = service.name;
                option.textContent = `${service.name} (₹${service.price})`;
                option.dataset.price = service.price;
                option.dataset.charge = service.charge;
                serviceSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading services:', error);
    }
}

async function loadStaffMembers() {
    try {
        const response = await fetch('/api/users?role=staff');
        const staff = await response.json();
        
        const assignedSelect = document.getElementById('assignedTo');
        if (assignedSelect) {
            assignedSelect.innerHTML = '<option value="">Assign Staff</option>';
            staff.forEach(member => {
                const option = document.createElement('option');
                option.value = member.username;
                option.textContent = `${member.name} (${member.username})`;
                assignedSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading staff:', error);
    }
}

async function loadTasks() {
    try {
        const response = await fetch('/api/tasks');
        const tasks = await response.json();
        renderTasks(tasks);
    } catch (error) {
        console.error('Error loading tasks:', error);
        showToast('Error loading tasks', 'error');
    }
}

function renderTasks(tasks) {
    const tbody = document.getElementById('taskTableBody');
    if (!tbody) return;

    if (tasks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align: center; padding: 40px; color: #999;">
                    <i class="fas fa-tasks" style="font-size: 48px; margin-bottom: 15px;"></i>
                    <p>No tasks found</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = '';
    tasks.forEach(task => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${task.order_no}</td>
            <td><strong>${task.customer_name}</strong></td>
            <td>${task.service_type}</td>
            <td>
                <span class="status-badge status-${task.status}">
                    ${formatStatus(task.status)}
                </span>
            </td>
            <td>${task.assigned_to}</td>
            <td>${task.shared_with || '-'}</td>
            <td>${formatDate(task.created_at)}</td>
            <td>${task.contact_number}</td>
            <td>
                <div class="action-buttons">
                    ${getActionButtons(task)}
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function getActionButtons(task) {
    const currentUser = getCurrentUser();
    let buttons = '';

    // View/Edit button
    buttons += `<button class="btn-action btn-view" onclick="viewTask(${task.id})" title="View Details">
        <i class="fas fa-eye"></i>
    </button>`;

    // Status change button (if allowed)
    if (canChangeStatus(task, currentUser)) {
        buttons += `<button class="btn-action btn-status" onclick="changeTaskStatus(${task.id})" title="Change Status">
            <i class="fas fa-exchange-alt"></i>
        </button>`;
    }

    // Complete with payment button
    if (task.status === 'pending' || task.status === 'in_progress') {
        buttons += `<button class="btn-action btn-complete" onclick="completeTask(${task.id})" title="Complete Task">
            <i class="fas fa-check-circle"></i>
        </button>`;
    }

    // Delete button (for admins/managers)
    if (currentUser.role === 'admin' || currentUser.role === 'manager') {
        buttons += `<button class="btn-action btn-delete" onclick="deleteTask(${task.id})" title="Delete Task">
            <i class="fas fa-trash"></i>
        </button>`;
    }

    return buttons;
}

async function changeTaskStatus(taskId) {
    // Get available status options
    const statusOptions = ['pending', 'in_progress', 'on_hold', 'delayed', 'cancelled', 'completed'];
    
    // Create modal for status change
    const modalHTML = `
        <div class="status-change-modal">
            <div class="modal-content">
                <h3>Change Task Status</h3>
                <div class="form-group">
                    <label for="newStatus">New Status</label>
                    <select id="newStatus" class="form-control">
                        ${statusOptions.map(status => 
                            `<option value="${status}">${formatStatus(status)}</option>`
                        ).join('')}
                    </select>
                </div>
                <div class="form-group">
                    <label for="statusReason">Reason (Required for cancellations and delays)</label>
                    <textarea id="statusReason" class="form-control" rows="3" 
                        placeholder="Enter reason for status change..."></textarea>
                </div>
                <div class="form-group">
                    <label for="customerMessage">Message to Customer (Auto-generated)</label>
                    <textarea id="customerMessage" class="form-control" rows="3" readonly></textarea>
                    <small>This message will be sent to the customer</small>
                </div>
                <div class="modal-actions">
                    <button class="btn" onclick="confirmStatusChange(${taskId})">Update Status</button>
                    <button class="btn cancel-btn" onclick="closeStatusModal()">Cancel</button>
                </div>
            </div>
        </div>
    `;

    // Add modal to page
    const modalContainer = document.createElement('div');
    modalContainer.innerHTML = modalHTML;
    document.body.appendChild(modalContainer);

    // Update customer message when status or reason changes
    document.getElementById('newStatus').addEventListener('change', updateCustomerMessage);
    document.getElementById('statusReason').addEventListener('input', updateCustomerMessage);

    // Initial message update
    updateCustomerMessage();
}

function updateCustomerMessage() {
    const status = document.getElementById('newStatus').value;
    const reason = document.getElementById('statusReason').value;
    
    const messages = {
        'pending': 'Your service request has been received and is pending processing.',
        'in_progress': 'Your service request is currently being processed.',
        'on_hold': 'Your service request is on hold. Reason: ' + reason,
        'completed': 'Your service request has been completed successfully!',
        'cancelled': 'Your service request has been cancelled. Reason: ' + reason,
        'delayed': 'Your service request has been delayed. Reason: ' + reason
    };
    
    const message = messages[status] || `Status updated to ${formatStatus(status)}.` + (reason ? ` Reason: ${reason}` : '');
    document.getElementById('customerMessage').value = message;
}

async function confirmStatusChange(taskId) {
    const newStatus = document.getElementById('newStatus').value;
    const reason = document.getElementById('statusReason').value;
    
    // Validate required reason for certain statuses
    if (['cancelled', 'delayed', 'on_hold'].includes(newStatus) && !reason.trim()) {
        showToast('Reason is required for this status change', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/tasks/${taskId}/status`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({status: newStatus, reason: reason})
        });

        const result = await response.json();
        
        if (result.success) {
            showToast('Status updated successfully', 'success');
            
            // Show customer message with copy button
            showCustomerMessage(result.customer_message);
            
            // Reload tasks
            loadTasks();
            closeStatusModal();
        } else {
            showToast(result.error || 'Failed to update status', 'error');
        }
    } catch (error) {
        console.error('Error updating status:', error);
        showToast('Error updating status', 'error');
    }
}

function showCustomerMessage(message) {
    const messageHTML = `
        <div class="customer-message-modal">
            <div class="modal-content">
                <h3><i class="fas fa-comment-alt"></i> Message to Send Customer</h3>
                <div class="message-content">
                    <textarea readonly>${message}</textarea>
                </div>
                <div class="message-actions">
                    <button class="btn" onclick="copyToClipboard('${message.replace(/'/g, "\\'")}')">
                        <i class="fas fa-copy"></i> Copy Message
                    </button>
                    <button class="btn" onclick="sendMessageToCustomer('${message.replace(/'/g, "\\'")}')">
                        <i class="fas fa-paper-plane"></i> Send via WhatsApp
                    </button>
                    <button class="btn cancel-btn" onclick="closeCustomerMessage()">Close</button>
                </div>
            </div>
        </div>
    `;

    const modalContainer = document.createElement('div');
    modalContainer.innerHTML = messageHTML;
    document.body.appendChild(modalContainer);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Message copied to clipboard', 'success');
    }).catch(err => {
        console.error('Copy failed:', err);
        showToast('Failed to copy message', 'error');
    });
}

function sendMessageToCustomer(message) {
    // Get customer phone number from current context
    // This would need to be implemented based on your app structure
    const phoneNumber = getCurrentCustomerPhone(); // Implement this function
    
    if (phoneNumber) {
        const encodedMessage = encodeURIComponent(message);
        const whatsappUrl = `https://wa.me/${phoneNumber}?text=${encodedMessage}`;
        window.open(whatsappUrl, '_blank');
    } else {
        showToast('Customer phone number not available', 'error');
    }
}

async function completeTask(taskId) {
    try {
        // Get task details
        const response = await fetch(`/api/tasks/${taskId}`);
        const task = await response.json();
        
        // Show payment modal
        showPaymentModal(task);
    } catch (error) {
        console.error('Error loading task:', error);
        showToast('Error loading task details', 'error');
    }
}

function showPaymentModal(task) {
    const dueAmount = task.due_amount || (task.service_price - task.paid_amount);
    
    document.getElementById('dueAmountDisplay').textContent = `₹${dueAmount.toLocaleString('en-IN')}`;
    document.getElementById('finalPaymentAmount').value = dueAmount;
    document.getElementById('finalPaymentAmount').max = dueAmount;
    
    // Store task ID in modal
    const modal = document.getElementById('paymentModal');
    modal.dataset.taskId = task.id;
    
    // Show modal
    modal.style.display = 'flex';
}

async function completeTaskWithPayment() {
    const modal = document.getElementById('paymentModal');
    const taskId = modal.dataset.taskId;
    
    const paymentAmount = parseFloat(document.getElementById('finalPaymentAmount').value);
    const paymode = document.getElementById('finalPaymode').value;
    const paymentNotes = document.getElementById('paymentNotes').value;
    
    if (!paymentAmount || paymentAmount <= 0) {
        showToast('Please enter a valid payment amount', 'error');
        return;
    }

    try {
        const response = await fetch(`/api/tasks/${taskId}/complete`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                final_payment_amount: paymentAmount,
                final_paymode: paymode,
                payment_notes: paymentNotes
            })
        });

        const result = await response.json();
        
        if (result.success) {
            showToast('Task completed successfully', 'success');
            closeModal('paymentModal');
            loadTasks();
        } else {
            showToast(result.error || 'Failed to complete task', 'error');
        }
    } catch (error) {
        console.error('Error completing task:', error);
        showToast('Error completing task', 'error');
    }
}

async function loadCustomerSuggestions() {
    const phoneInput = document.getElementById('contactNumber');
    const phone = phoneInput.value.replace(/\D/g, '');
    
    if (phone.length >= 3) {
        try {
            const response = await fetch(`/api/customers/suggest?phone=${phone}`);
            const suggestions = await response.json();
            
            showCustomerSuggestions(suggestions);
        } catch (error) {
            console.error('Error loading suggestions:', error);
        }
    }
}

function showCustomerSuggestions(suggestions) {
    // Create suggestions dropdown
    const dropdown = document.createElement('div');
    dropdown.className = 'customer-suggestions';
    
    if (suggestions.length === 0) {
        dropdown.innerHTML = '<div class="suggestion-item">No previous customers found</div>';
    } else {
        dropdown.innerHTML = suggestions.map(customer => `
            <div class="suggestion-item" onclick="selectCustomerSuggestion('${customer.name}', '${customer.contact_number}')">
                <strong>${customer.name}</strong>
                <small>${customer.contact_number}</small>
                <span class="customer-rating">${'★'.repeat(customer.rating)}</span>
                <span class="customer-orders">${customer.total_orders} orders</span>
            </div>
        `).join('');
    }
    
    // Position and show dropdown
    const phoneInput = document.getElementById('contactNumber');
    phoneInput.parentNode.appendChild(dropdown);
}

function selectCustomerSuggestion(name, phone) {
    document.getElementById('customerName').value = name;
    document.getElementById('contactNumber').value = phone;
    
    // Remove suggestions dropdown
    const dropdown = document.querySelector('.customer-suggestions');
    if (dropdown) dropdown.remove();
}

async function autoFillCustomerName(phone) {
    try {
        const response = await fetch(`/api/customers/search?q=${phone}`);
        const customers = await response.json();
        
        if (customers.length > 0) {
            document.getElementById('customerName').value = customers[0].name;
        }
    } catch (error) {
        console.error('Error searching customer:', error);
    }
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function formatStatus(status) {
    const statusMap = {
        'pending': 'Pending',
        'in_progress': 'In Progress',
        'on_hold': 'On Hold',
        'completed': 'Completed',
        'cancelled': 'Cancelled',
        'delayed': 'Delayed'
    };
    return statusMap[status] || status;
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    });
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    toast.querySelector('#toastMessage').textContent = message;
    toast.className = `toast toast-${type}`;
    toast.style.display = 'flex';
    
    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}

function getCurrentUser() {
    // This should be populated from your authentication system
    return {
        username: sessionStorage.getItem('username') || 'staff',
        role: sessionStorage.getItem('role') || 'staff',
        name: sessionStorage.getItem('name') || 'Staff Member'
    };
}

function canChangeStatus(task, user) {
    // Define who can change status
    if (user.role === 'admin' || user.role === 'manager') return true;
    if (user.role === 'staff' && task.assigned_to === user.username) return true;
    return false;
}

// Modal management functions
function closeStatusModal() {
    const modal = document.querySelector('.status-change-modal');
    if (modal) modal.remove();
}

function closeCustomerMessage() {
    const modal = document.querySelector('.customer-message-modal');
    if (modal) modal.remove();
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'none';
}