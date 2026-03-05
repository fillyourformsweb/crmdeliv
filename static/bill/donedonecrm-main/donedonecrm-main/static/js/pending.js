// Configuration
const API_BASE_URL = '/api';
let currentPage = 1;
const itemsPerPage = 10;
let totalTasks = 0;

// DOM Elements
const tasksBody = document.getElementById('tasks-body');
const updateModal = document.getElementById('update-modal');
const detailsModal = document.getElementById('details-modal');
const updateForm = document.getElementById('update-status-form');
const searchInput = document.getElementById('search-tasks');
const filterStatus = document.getElementById('filter-status');
const prevPageBtn = document.getElementById('prev-page');
const nextPageBtn = document.getElementById('next-page');
const pageInfo = document.getElementById('page-info');

// Load pending tasks
async function loadPendingTasks() {
    try {
        showLoading();
        
        const response = await fetch(`${API_BASE_URL}/staff/pending-tasks?page=${currentPage}&limit=${itemsPerPage}`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) throw new Error('Failed to fetch tasks');
        
        const data = await response.json();
        totalTasks = data.total || 0;
        
        updateStats(data.stats || {});
        renderTasks(data.tasks || []);
        updatePagination();
        
    } catch (error) {
        console.error('Error loading tasks:', error);
        showToast('Failed to load tasks. Please try again.', 'error');
        renderError();
    }
}

// Show loading state
function showLoading() {
    tasksBody.innerHTML = `
        <tr class="loading-row">
            <td colspan="8">
                <div class="loading-spinner">
                    <i class="fas fa-spinner fa-spin"></i>
                    Loading tasks...
                </div>
            </td>
        </tr>
    `;
}

// Render tasks table
function renderTasks(tasks) {
    if (tasks.length === 0) {
        tasksBody.innerHTML = `
            <tr>
                <td colspan="8" class="no-tasks">
                    <div class="empty-state">
                        <i class="fas fa-inbox"></i>
                        <h3>No pending tasks found</h3>
                        <p>All your tasks are up to date!</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    const tasksHtml = tasks.map(task => `
        <tr data-task-id="${task.id}">
            <td>#${task.id}</td>
            <td>
                <strong>${escapeHtml(task.title)}</strong>
                ${task.description ? `<br><small class="text-muted">${escapeHtml(task.description.substring(0, 50))}...</small>` : ''}
            </td>
            <td>${escapeHtml(task.project || 'General')}</td>
            <td>
                <span class="priority-${task.priority || 'medium'}">
                    ${task.priority ? task.priority.charAt(0).toUpperCase() + task.priority.slice(1) : 'Medium'}
                </span>
            </td>
            <td>
                ${formatDate(task.pending_since)}
                ${isOverdue(task.reminder_date) ? '<br><small class="text-danger">Overdue</small>' : ''}
            </td>
            <td>${task.reminder_date ? formatDate(task.reminder_date) : 'Not set'}</td>
            <td>
                ${task.pending_reason ? `<small>${escapeHtml(task.pending_reason.substring(0, 50))}...</small>` : 'No reason provided'}
            </td>
            <td>
                <div class="action-buttons">
                    <button class="btn-action btn-edit" onclick="openUpdateModal('${task.id}')">
                        <i class="fas fa-edit"></i> Update
                    </button>
                    <button class="btn-action btn-view" onclick="viewTaskDetails('${task.id}')">
                        <i class="fas fa-eye"></i> View
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
    
    tasksBody.innerHTML = tasksHtml;
}

// Update statistics
function updateStats(stats) {
    document.getElementById('total-pending').textContent = stats.total || 0;
    document.getElementById('reminders-count').textContent = stats.with_reminders || 0;
    document.getElementById('overdue-count').textContent = stats.overdue || 0;
}

// Update pagination controls
function updatePagination() {
    const totalPages = Math.ceil(totalTasks / itemsPerPage);
    
    prevPageBtn.disabled = currentPage <= 1;
    nextPageBtn.disabled = currentPage >= totalPages;
    
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
}

// Open update modal
async function openUpdateModal(taskId) {
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) throw new Error('Failed to fetch task details');
        
        const task = await response.json();
        
        // Populate form
        document.getElementById('task-id').value = task.id;
        document.getElementById('new-status').value = task.status || '';
        document.getElementById('pending-reason').value = task.pending_reason || '';
        
        if (task.reminder_date) {
            document.getElementById('reminder-date').value = formatDateForInput(task.reminder_date);
        }
        
        if (task.expected_end_date) {
            document.getElementById('end-date').value = formatDateForInput(task.expected_end_date);
        }
        
        // Show modal
        updateModal.classList.add('active');
        
    } catch (error) {
        console.error('Error loading task:', error);
        showToast('Failed to load task details.', 'error');
    }
}

// Update task status
async function updateTaskStatus() {
    const taskId = document.getElementById('task-id').value;
    const formData = {
        status: document.getElementById('new-status').value,
        pending_reason: document.getElementById('pending-reason').value,
        reminder_date: document.getElementById('reminder-date').value || null,
        expected_end_date: document.getElementById('end-date').value || null,
        set_reminder: document.getElementById('set-reminder').checked,
        notify_manager: document.getElementById('notify-manager').checked
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) throw new Error('Failed to update task');
        
        const result = await response.json();
        
        showToast('Task status updated successfully!', 'success');
        updateModal.classList.remove('active');
        updateForm.reset();
        
        // Reload tasks
        loadPendingTasks();
        
    } catch (error) {
        console.error('Error updating task:', error);
        showToast('Failed to update task status.', 'error');
    }
}

// View task details
async function viewTaskDetails(taskId) {
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/details`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) throw new Error('Failed to fetch task details');
        
        const task = await response.json();
        
        const detailsHtml = `
            <div class="task-detail-item">
                <div class="task-detail-label">
                    <i class="fas fa-heading"></i> Title
                </div>
                <div class="task-detail-value">${escapeHtml(task.title)}</div>
            </div>
            
            <div class="task-detail-item">
                <div class="task-detail-label">
                    <i class="fas fa-align-left"></i> Description
                </div>
                <div class="task-detail-value">${escapeHtml(task.description || 'No description')}</div>
            </div>
            
            <div class="task-detail-item">
                <div class="task-detail-label">
                    <i class="fas fa-project-diagram"></i> Project
                </div>
                <div class="task-detail-value">${escapeHtml(task.project || 'General')}</div>
            </div>
            
            <div class="task-detail-item">
                <div class="task-detail-label">
                    <i class="fas fa-flag"></i> Priority
                </div>
                <div class="task-detail-value">
                    <span class="priority-${task.priority || 'medium'}">
                        ${task.priority ? task.priority.charAt(0).toUpperCase() + task.priority.slice(1) : 'Medium'}
                    </span>
                </div>
            </div>
            
            <div class="task-detail-item">
                <div class="task-detail-label">
                    <i class="fas fa-calendar-alt"></i> Created
                </div>
                <div class="task-detail-value">${formatDate(task.created_at)}</div>
            </div>
            
            <div class="task-detail-item">
                <div class="task-detail-label">
                    <i class="fas fa-clock"></i> Pending Since
                </div>
                <div class="task-detail-value">${formatDate(task.pending_since)}</div>
            </div>
            
            <div class="task-detail-item">
                <div class="task-detail-label">
                    <i class="fas fa-bell"></i> Reminder Date
                </div>
                <div class="task-detail-value">${task.reminder_date ? formatDate(task.reminder_date) : 'Not set'}</div>
            </div>
            
            <div class="task-detail-item">
                <div class="task-detail-label">
                    <i class="fas fa-calendar-check"></i> Expected End Date
                </div>
                <div class="task-detail-value">${task.expected_end_date ? formatDate(task.expected_end_date) : 'Not set'}</div>
            </div>
            
            <div class="task-detail-item">
                <div class="task-detail-label">
                    <i class="fas fa-comment"></i> Pending Reason
                </div>
                <div class="task-detail-value">${escapeHtml(task.pending_reason || 'No reason provided')}</div>
            </div>
            
            <div class="task-detail-item">
                <div class="task-detail-label">
                    <i class="fas fa-sticky-note"></i> Additional Notes
                </div>
                <div class="task-detail-value">${escapeHtml(task.notes || 'No additional notes')}</div>
            </div>
        `;
        
        document.getElementById('task-details-content').innerHTML = detailsHtml;
        detailsModal.classList.add('active');
        
    } catch (error) {
        console.error('Error loading task details:', error);
        showToast('Failed to load task details.', 'error');
    }
}

// Show toast notification
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.style.display = 'block';
    
    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}

// Utility functions
function getAuthToken() {
    // This should be implemented based on your authentication system
    return localStorage.getItem('auth_token') || '';
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatDateForInput(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toISOString().slice(0, 16);
}

function isOverdue(dateString) {
    if (!dateString) return false;
    const date = new Date(dateString);
    return date < new Date();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderError() {
    tasksBody.innerHTML = `
        <tr>
            <td colspan="8" class="error-state">
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h3>Failed to load tasks</h3>
                    <p>Please try refreshing the page.</p>
                    <button onclick="loadPendingTasks()" class="btn btn-primary">
                        <i class="fas fa-redo"></i> Retry
                    </button>
                </div>
            </td>
        </tr>
    `;
}

// Event Listeners
prevPageBtn.addEventListener('click', () => {
    if (currentPage > 1) {
        currentPage--;
        loadPendingTasks();
    }
});

nextPageBtn.addEventListener('click', () => {
    const totalPages = Math.ceil(totalTasks / itemsPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        loadPendingTasks();
    }
});

searchInput.addEventListener('input', debounce(() => {
    currentPage = 1;
    loadPendingTasks();
}, 300));

filterStatus.addEventListener('change', () => {
    currentPage = 1;
    loadPendingTasks();
});

// Debounce function for search
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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadPendingTasks();
    
    // Auto-refresh every 5 minutes
    setInterval(loadPendingTasks, 5 * 60 * 1000);
});