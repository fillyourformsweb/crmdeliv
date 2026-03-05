// openplace.js - OpenPlace Management
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const refreshBtn = document.getElementById('refreshOpenPlace');
    const filterToggleBtn = document.getElementById('filterToggleBtn');
    const filterContainer = document.getElementById('filterContainer');
    const applyFiltersBtn = document.getElementById('applyFilters');
    const resetFiltersBtn = document.getElementById('resetFilters');
    const searchBox = document.getElementById('searchOpenPlace');
    const openplaceTableBody = document.getElementById('openplaceTableBody');
    const claimedTableBody = document.getElementById('claimedTableBody');
    const availableTasksCount = document.getElementById('availableTasksCount');
    const myClaimedTasksCount = document.getElementById('myClaimedTasksCount');
    const totalClaimedCount = document.getElementById('totalClaimedCount');
    const totalValue = document.getElementById('totalValue');
    const openplaceTaskCount = document.getElementById('openplaceTaskCount');
    const taskDetailsModal = document.getElementById('taskDetailsModal');
    const closeDetailsModal = document.getElementById('closeDetailsModal');
    const closeDetailsBtn = document.getElementById('closeDetailsBtn');
    const claimTaskBtn = document.getElementById('claimTaskBtn');
    const claimConfirmationModal = document.getElementById('claimConfirmationModal');
    const closeClaimModal = document.getElementById('closeClaimModal');
    const cancelClaimBtn = document.getElementById('cancelClaimBtn');
    const confirmClaimBtn = document.getElementById('confirmClaimBtn');
    const claimTaskPreview = document.getElementById('claimTaskPreview');
    
    // State variables
    let openplaceTasks = [];
    let claimedTasks = [];
    let currentTaskId = null;
    let filters = {
        branch: 'all',
        service: 'all',
        date: 'all',
        priority: 'all'
    };
    
    // Initialize
    initializePage();
    
    // Event Listeners
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadOpenPlaceTasks);
    }
    
    if (filterToggleBtn) {
        filterToggleBtn.addEventListener('click', function() {
            filterContainer.classList.toggle('hidden');
            filterToggleBtn.classList.toggle('active');
        });
    }
    
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }
    
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', resetFilters);
    }
    
    if (searchBox) {
        searchBox.addEventListener('input', searchTasks);
    }
    
    if (closeDetailsModal) {
        closeDetailsModal.addEventListener('click', closeTaskDetails);
    }
    
    if (closeDetailsBtn) {
        closeDetailsBtn.addEventListener('click', closeTaskDetails);
    }
    
    if (claimTaskBtn) {
        claimTaskBtn.addEventListener('click', openClaimConfirmation);
    }
    
    if (closeClaimModal) {
        closeClaimModal.addEventListener('click', closeClaimConfirmation);
    }
    
    if (cancelClaimBtn) {
        cancelClaimBtn.addEventListener('click', closeClaimConfirmation);
    }
    
    if (confirmClaimBtn) {
        confirmClaimBtn.addEventListener('click', claimTask);
    }
    
    // Close modals when clicking outside
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            event.target.classList.remove('active');
        }
    });
    
    // Functions
    function initializePage() {
        // Set current date
        const currentDate = document.getElementById('currentDate');
        if (currentDate) {
            currentDate.textContent = new Date().toLocaleDateString('en-GB', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        }
        
        // Load initial data
        loadOpenPlaceTasks();
        loadClaimedTasks();
        populateServiceDropdown();
    }
    
    async function loadOpenPlaceTasks() {
        try {
            showLoading(openplaceTableBody);
            
            // Fetch tasks from API
            const response = await fetch('/api/openplace/tasks');
            const data = await response.json();
            
            if (data.tasks) {
                openplaceTasks = data.tasks;
                updateStatistics();
                renderOpenPlaceTasks();
            }
        } catch (error) {
            console.error('Error loading OpenPlace tasks:', error);
            showError(openplaceTableBody, 'Failed to load tasks');
        }
    }
    
    async function loadClaimedTasks() {
        try {
            // In real implementation, fetch claimed tasks from API
            // For now, we'll use a simulated response
            const claimed = openplaceTasks.filter(task => task.status === 'Claimed');
            claimedTasks = claimed;
            
            renderClaimedTasks();
            updateStatistics();
        } catch (error) {
            console.error('Error loading claimed tasks:', error);
        }
    }
    
    function populateServiceDropdown() {
        const filterService = document.getElementById('filterService');
        if (!filterService) return;
        
        // Fetch services from API
        fetch('/api/tasks/services')
            .then(response => response.json())
            .then(data => {
                filterService.innerHTML = '<option value="all">All Services</option>';
                data.services.forEach(service => {
                    const option = document.createElement('option');
                    option.value = service.name;
                    option.textContent = service.name;
                    filterService.appendChild(option);
                });
            })
            .catch(error => console.error('Error loading services:', error));
    }
    
    function renderOpenPlaceTasks() {
        if (!openplaceTableBody) return;
        
        // Apply filters
        let filteredTasks = [...openplaceTasks];
        
        if (filters.branch !== 'all') {
            filteredTasks = filteredTasks.filter(task => task.branch_code === filters.branch);
        }
        
        if (filters.service !== 'all') {
            filteredTasks = filteredTasks.filter(task => task.service_type === filters.service);
        }
        
        if (filters.priority !== 'all') {
            filteredTasks = filteredTasks.filter(task => task.priority === filters.priority);
        }
        
        // Apply date filter
        filteredTasks = filterByDate(filteredTasks);
        
        // Apply search
        if (searchBox.value) {
            const searchTerm = searchBox.value.toLowerCase();
            filteredTasks = filteredTasks.filter(task => 
                task.customer_name.toLowerCase().includes(searchTerm) ||
                task.service_type.toLowerCase().includes(searchTerm) ||
                task.description?.toLowerCase().includes(searchTerm) ||
                task.inquiry_no?.toLowerCase().includes(searchTerm)
            );
        }
        
        // Only show available tasks (not claimed)
        filteredTasks = filteredTasks.filter(task => task.status === 'Open' || task.status === 'Available');
        
        openplaceTableBody.innerHTML = '';
        
        if (filteredTasks.length === 0) {
            showEmptyState(openplaceTableBody, 'No tasks available', 'All tasks have been claimed or no tasks match your filters');
            return;
        }
        
        filteredTasks.forEach(task => {
            const row = document.createElement('tr');
            
            // Format date
            const taskDate = new Date(task.date_created);
            const formattedDate = taskDate.toLocaleDateString('en-GB');
            const timeAgo = getTimeAgo(taskDate);
            
            row.innerHTML = `
                <td>${task.inquiry_no || task.id}</td>
                <td>${task.customer_name}</td>
                <td>${task.service_type}</td>
                <td>${task.branch_code}</td>
                <td>${task.requested_by_name || 'System'}</td>
                <td>
                    ${formattedDate}<br>
                    <small class="text-muted">${timeAgo}</small>
                </td>
                <td><strong>₹${task.estimated_price || task.service_price || '0'}</strong></td>
                <td>
                    <span class="task-priority priority-${task.priority?.toLowerCase() || 'medium'}">
                        ${task.priority || 'Medium'}
                    </span>
                </td>
                <td>
                    <span class="status-badge status-${task.status.toLowerCase()}">
                        ${task.status}
                    </span>
                </td>
                <td class="actions-cell">
                    <button class="action-btn view" onclick="viewTask('${task.id}')" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="action-btn claim" onclick="prepareClaim('${task.id}')" title="Claim Task">
                        <i class="fas fa-hand-paper"></i>
                    </button>
                </td>
            `;
            
            openplaceTableBody.appendChild(row);
        });
        
        // Update task count
        openplaceTaskCount.textContent = `${filteredTasks.length} task${filteredTasks.length !== 1 ? 's' : ''}`;
    }
    
    function renderClaimedTasks() {
        if (!claimedTableBody) return;
        
        // Filter tasks claimed by current user
        const myClaimedTasks = claimedTasks.filter(task => 
            task.claimed_by === currentUser.id
        );
        
        claimedTableBody.innerHTML = '';
        
        if (myClaimedTasks.length === 0) {
            claimedTableBody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 40px; color: #999;">
                        <i class="fas fa-inbox" style="font-size: 32px; margin-bottom: 10px;"></i>
                        <p>No claimed tasks yet</p>
                        <small>Claim tasks from the table above to see them here</small>
                    </td>
                </tr>
            `;
            return;
        }
        
        myClaimedTasks.forEach(task => {
            const row = document.createElement('tr');
            
            // Format dates
            const createdDate = new Date(task.date_created);
            const formattedCreatedDate = createdDate.toLocaleDateString('en-GB');
            const claimedDate = task.claimed_date ? new Date(task.claimed_date) : createdDate;
            const formattedClaimedDate = claimedDate.toLocaleDateString('en-GB');
            
            row.innerHTML = `
                <td>${task.inquiry_no || task.id}</td>
                <td>${task.customer_name}</td>
                <td>${task.service_type}</td>
                <td>${task.branch_code}</td>
                <td>${formattedClaimedDate}</td>
                <td><strong>₹${task.estimated_price || task.service_price || '0'}</strong></td>
                <td>
                    <span class="status-badge status-inprogress">
                        In Progress
                    </span>
                </td>
                <td class="actions-cell">
                    <button class="action-btn view" onclick="viewTask('${task.id}')" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="action-btn edit" onclick="convertToTask('${task.id}')" title="Convert to Task">
                        <i class="fas fa-exchange-alt"></i>
                    </button>
                </td>
            `;
            
            claimedTableBody.appendChild(row);
        });
    }
    
    function updateStatistics() {
        // Available tasks
        const availableTasks = openplaceTasks.filter(task => 
            task.status === 'Open' || task.status === 'Available'
        );
        
        // Tasks claimed by current user
        const myClaimed = claimedTasks.filter(task => 
            task.claimed_by === currentUser.id
        );
        
        // Total claimed tasks
        const totalClaimed = claimedTasks.length;
        
        // Total value
        const totalValueAmount = availableTasks.reduce((sum, task) => 
            sum + (task.estimated_price || task.service_price || 0), 0
        );
        
        // Update UI
        availableTasksCount.textContent = availableTasks.length;
        myClaimedTasksCount.textContent = myClaimed.length;
        totalClaimedCount.textContent = totalClaimed;
        totalValue.textContent = `₹${totalValueAmount.toLocaleString()}`;
    }
    
    function applyFilters() {
        const filterBranch = document.getElementById('filterBranch');
        const filterService = document.getElementById('filterService');
        const filterDate = document.getElementById('filterDate');
        const filterPriority = document.getElementById('filterPriority');
        
        filters = {
            branch: filterBranch?.value || 'all',
            service: filterService?.value || 'all',
            date: filterDate?.value || 'all',
            priority: filterPriority?.value || 'all'
        };
        
        renderOpenPlaceTasks();
    }
    
    function resetFilters() {
        const filterBranch = document.getElementById('filterBranch');
        const filterService = document.getElementById('filterService');
        const filterDate = document.getElementById('filterDate');
        const filterPriority = document.getElementById('filterPriority');
        
        if (filterBranch) filterBranch.value = 'all';
        if (filterService) filterService.value = 'all';
        if (filterDate) filterDate.value = 'all';
        if (filterPriority) filterPriority.value = 'all';
        
        filters = {
            branch: 'all',
            service: 'all',
            date: 'all',
            priority: 'all'
        };
        
        searchBox.value = '';
        renderOpenPlaceTasks();
    }
    
    function filterByDate(tasks) {
        if (filters.date === 'all') return tasks;
        
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        
        return tasks.filter(task => {
            const taskDate = new Date(task.date_created);
            taskDate.setHours(0, 0, 0, 0);
            
            switch(filters.date) {
                case 'today':
                    return taskDate.getTime() === today.getTime();
                case 'yesterday':
                    const yesterday = new Date(today);
                    yesterday.setDate(yesterday.getDate() - 1);
                    return taskDate.getTime() === yesterday.getTime();
                case 'last7':
                    const lastWeek = new Date(today);
                    lastWeek.setDate(lastWeek.getDate() - 7);
                    return taskDate >= lastWeek;
                case 'last30':
                    const lastMonth = new Date(today);
                    lastMonth.setDate(lastMonth.getDate() - 30);
                    return taskDate >= lastMonth;
                default:
                    return true;
            }
        });
    }
    
    function searchTasks() {
        renderOpenPlaceTasks();
    }
    
    function viewTask(taskId) {
        const task = openplaceTasks.find(t => t.id === taskId);
        if (!task) return;
        
        currentTaskId = taskId;
        
        // Format dates
        const createdDate = new Date(task.date_created);
        const formattedDate = createdDate.toLocaleDateString('en-GB', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        const taskDetailsContent = document.getElementById('taskDetailsContent');
        taskDetailsContent.innerHTML = `
            <div class="details-grid">
                <div class="detail-item">
                    <strong>Task ID:</strong>
                    <div class="detail-content">${task.inquiry_no || task.id}</div>
                </div>
                <div class="detail-item">
                    <strong>Customer Name:</strong>
                    <div class="detail-content">${task.customer_name}</div>
                </div>
                <div class="detail-item">
                    <strong>Contact Number:</strong>
                    <div class="detail-content">${task.contact_number || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <strong>Email:</strong>
                    <div class="detail-content">${task.email || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <strong>Branch:</strong>
                    <div class="detail-content">${task.branch_code}</div>
                </div>
                <div class="detail-item">
                    <strong>Service Required:</strong>
                    <div class="detail-content">${task.service_type}</div>
                </div>
                <div class="detail-item">
                    <strong>Estimated Price:</strong>
                    <div class="detail-content"><strong>₹${task.estimated_price || task.service_price || '0'}</strong></div>
                </div>
                <div class="detail-item">
                    <strong>Priority:</strong>
                    <div class="detail-content">
                        <span class="task-priority priority-${task.priority?.toLowerCase() || 'medium'}">
                            ${task.priority || 'Medium'}
                        </span>
                    </div>
                </div>
                <div class="detail-item">
                    <strong>Status:</strong>
                    <div class="detail-content">
                        <span class="status-badge status-${task.status.toLowerCase()}">
                            ${task.status}
                        </span>
                    </div>
                </div>
                <div class="detail-item">
                    <strong>Posted By:</strong>
                    <div class="detail-content">${task.requested_by_name || 'System'}</div>
                </div>
                <div class="detail-item">
                    <strong>Date Posted:</strong>
                    <div class="detail-content">${formattedDate}</div>
                </div>
                <div class="detail-item full-width">
                    <strong>Description:</strong>
                    <div class="detail-content">${task.description || task.notes || 'No description provided'}</div>
                </div>
                <div class="detail-item full-width">
                    <strong>Additional Notes:</strong>
                    <div class="detail-content">${task.additional_notes || 'No additional notes'}</div>
                </div>
            </div>
        `;
        
        taskDetailsModal.classList.add('active');
    }
    
    function closeTaskDetails() {
        taskDetailsModal.classList.remove('active');
        currentTaskId = null;
    }
    
    function prepareClaim(taskId) {
        const task = openplaceTasks.find(t => t.id === taskId);
        if (!task) return;
        
        currentTaskId = taskId;
        
        claimTaskPreview.innerHTML = `
            <div class="task-preview-item">
                <span class="task-preview-label">Task ID:</span>
                <span class="task-preview-value">${task.inquiry_no || task.id}</span>
            </div>
            <div class="task-preview-item">
                <span class="task-preview-label">Customer:</span>
                <span class="task-preview-value">${task.customer_name}</span>
            </div>
            <div class="task-preview-item">
                <span class="task-preview-label">Service:</span>
                <span class="task-preview-value">${task.service_type}</span>
            </div>
            <div class="task-preview-item">
                <span class="task-preview-label">Estimated Price:</span>
                <span class="task-preview-value"><strong>₹${task.estimated_price || task.service_price || '0'}</strong></span>
            </div>
            <div class="task-preview-item">
                <span class="task-preview-label">Branch:</span>
                <span class="task-preview-value">${task.branch_code}</span>
            </div>
        `;
        
        // Close details modal if open
        taskDetailsModal.classList.remove('active');
        
        // Open confirmation modal
        claimConfirmationModal.classList.add('active');
    }
    
    function openClaimConfirmation() {
        if (!currentTaskId) return;
        prepareClaim(currentTaskId);
    }
    
    function closeClaimConfirmation() {
        claimConfirmationModal.classList.remove('active');
        currentTaskId = null;
    }
    
    async function claimTask() {
        if (!currentTaskId) return;
        
        try {
            const response = await fetch(`/api/openplace/tasks/${currentTaskId}/claim`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast('Task claimed successfully!', 'success');
                
                // Reload tasks
                await loadOpenPlaceTasks();
                await loadClaimedTasks();
                
                // Close modals
                closeClaimConfirmation();
                closeTaskDetails();
            } else {
                showToast(data.error || 'Failed to claim task', 'error');
            }
        } catch (error) {
            console.error('Error claiming task:', error);
            showToast('Error claiming task', 'error');
        }
    }
    
    function convertToTask(taskId) {
        // Redirect to tasks page with pre-filled data
        const task = openplaceTasks.find(t => t.id === taskId);
        if (task) {
            showToast(`Converting task ${task.inquiry_no || task.id} to regular task`, 'info');
            // In real implementation, you would redirect to tasks page with data
            window.location.href = `/staff/tasks?inquiry=${encodeURIComponent(JSON.stringify(task))}`;
        }
    }
    
    // Utility functions
    function getTimeAgo(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 60) {
            return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
        } else if (diffHours < 24) {
            return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        } else if (diffDays < 30) {
            return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
        } else {
            return 'Over a month ago';
        }
    }
    
    function showLoading(container) {
        if (!container) return;
        container.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 40px;">
                    <div class="loading-state">
                        <i class="fas fa-spinner fa-spin loading-spinner"></i>
                        <p>Loading tasks...</p>
                    </div>
                </td>
            </tr>
        `;
    }
    
    function showError(container, message) {
        if (!container) return;
        container.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 40px; color: #dc3545;">
                    <i class="fas fa-exclamation-circle" style="font-size: 32px; margin-bottom: 10px;"></i>
                    <p>${message}</p>
                    <button class="btn btn-sm" onclick="location.reload()">
                        <i class="fas fa-redo"></i> Retry
                    </button>
                </td>
            </tr>
        `;
    }
    
    function showEmptyState(container, title, message) {
        if (!container) return;
        container.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 50px 20px;">
                    <div class="empty-state">
                        <i class="fas fa-inbox" style="font-size: 48px; margin-bottom: 20px;"></i>
                        <h4>${title}</h4>
                        <p>${message}</p>
                        <button class="btn" onclick="resetFilters()">
                            <i class="fas fa-redo"></i> Reset Filters
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }
    
    function showToast(message, type = 'success') {
        let toast = document.getElementById('toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'toast';
            toast.className = 'toast';
            document.body.appendChild(toast);
        }
        
        const icon = toast.querySelector('i') || document.createElement('i');
        const messageSpan = toast.querySelector('#toastMessage') || document.createElement('span');
        messageSpan.id = 'toastMessage';
        
        toast.innerHTML = '';
        
        // Set icon based on type
        if (type === 'error') {
            icon.className = 'fas fa-exclamation-circle';
            toast.classList.add('error');
        } else if (type === 'warning') {
            icon.className = 'fas fa-exclamation-triangle';
            toast.classList.add('warning');
        } else if (type === 'info') {
            icon.className = 'fas fa-info-circle';
        } else {
            icon.className = 'fas fa-check-circle';
        }
        
        messageSpan.textContent = message;
        
        toast.appendChild(icon);
        toast.appendChild(messageSpan);
        
        // Show toast
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        // Hide after 3 seconds
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
    
    // Make functions available globally
    window.viewTask = viewTask;
    window.prepareClaim = prepareClaim;
    window.convertToTask = convertToTask;
});