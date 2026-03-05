// DOM Elements
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');
const addServiceBtn = document.getElementById('addServiceBtn');
const serviceFormContainer = document.getElementById('serviceFormContainer');
const serviceForm = document.getElementById('serviceForm');
const cancelServiceBtn = document.getElementById('cancelServiceBtn');
const deleteServiceBtn = document.getElementById('deleteServiceBtn');
const serviceListContainer = document.getElementById('serviceListContainer');
const serviceSearch = document.getElementById('serviceSearch');
const serviceFormTitle = document.getElementById('serviceFormTitle');
const serviceIdInput = document.getElementById('serviceId');

// API Base URL
const API_BASE_URL = '/api/services';

// Sidebar toggle functionality
sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
    const icon = sidebarToggle.querySelector('i');
    if (sidebar.classList.contains('collapsed')) {
        icon.className = 'fas fa-bars';
    } else {
        icon.className = 'fas fa-times';
    }
});

// Add service button click
addServiceBtn.addEventListener('click', () => {
    resetForm();
    serviceFormTitle.textContent = 'Add New Service';
    deleteServiceBtn.classList.add('hidden');
    serviceFormContainer.classList.remove('hidden');
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
});

// Cancel service form
cancelServiceBtn.addEventListener('click', () => {
    serviceFormContainer.classList.add('hidden');
    resetForm();
});

// Service form submission
serviceForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const serviceId = parseInt(serviceIdInput.value);
    const serviceData = {
        name: document.getElementById('serviceName').value,
        price: parseFloat(document.getElementById('servicePriceDB').value) || 0,
        fee: parseFloat(document.getElementById('serviceFee').value) || 0,
        charge: parseFloat(document.getElementById('serviceChargeDB').value) || 0,
        link: document.getElementById('serviceLink').value,
        note: document.getElementById('serviceNote').value,
        status: document.getElementById('serviceStatus').value
    };
    
    try {
        let response;
        
        if (serviceId) {
            // Update existing service
            response = await fetch(`${API_BASE_URL}/${serviceId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(serviceData)
            });
        } else {
            // Add new service
            response = await fetch(API_BASE_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(serviceData)
            });
        }
        
        const result = await response.json();
        
        if (result.success) {
            loadServices();
            serviceFormContainer.classList.add('hidden');
            resetForm();
            showNotification(result.message, 'success');
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        console.error('Error saving service:', error);
        showNotification('Error saving service. Please try again.', 'error');
    }
});

// Delete service
deleteServiceBtn.addEventListener('click', async () => {
    const serviceId = parseInt(serviceIdInput.value);
    if (serviceId && confirm('Are you sure you want to delete this service?')) {
        try {
            const response = await fetch(`${API_BASE_URL}/${serviceId}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                loadServices();
                serviceFormContainer.classList.add('hidden');
                resetForm();
                showNotification(result.message, 'success');
            } else {
                showNotification(result.message, 'error');
            }
        } catch (error) {
            console.error('Error deleting service:', error);
            showNotification('Error deleting service. Please try again.', 'error');
        }
    }
});

// Search functionality
serviceSearch.addEventListener('input', debounce(async (e) => {
    const searchTerm = e.target.value;
    await loadServices(searchTerm);
}, 300));

// Load services from API
async function loadServices(search = '') {
    try {
        showLoading(true);
        
        const url = search ? `${API_BASE_URL}?search=${encodeURIComponent(search)}` : API_BASE_URL;
        const response = await fetch(url);
        const services = await response.json();
        
        renderServices(services);
        showLoading(false);
    } catch (error) {
        console.error('Error loading services:', error);
        showLoading(false);
        showNotification('Error loading services. Please try again.', 'error');
    }
}

// Render services to the table
function renderServices(services) {
    serviceListContainer.innerHTML = '';
    
    if (services.length === 0) {
        serviceListContainer.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 40px;">
                    <i class="fas fa-box-open" style="font-size: 48px; color: #ddd; margin-bottom: 15px;"></i>
                    <p style="color: #999;">No services found. Add your first service!</p>
                </td>
            </tr>
        `;
        return;
    }
    
    services.forEach(service => {
        const profit = service.profit || (service.charge - service.fee);
        const profitColor = profit >= 0 ? 'var(--success-color)' : 'var(--danger-color)';
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <div style="font-weight: 500;">${service.name}</div>
                ${service.note ? `<div style="font-size: 12px; color: var(--gray-color); margin-top: 5px;">${service.note.substring(0, 50)}${service.note.length > 50 ? '...' : ''}</div>` : ''}
            </td>
            <td class="price-cell">₹${service.price.toLocaleString('en-IN')}</td>
            <td>₹${service.fee.toLocaleString('en-IN')}</td>
            <td>₹${service.charge.toLocaleString('en-IN')}</td>
            <td style="color: ${profitColor}; font-weight: 600;">₹${profit.toLocaleString('en-IN')}</td>
            <td>
                <span class="status-${service.status}">${service.status === 'active' ? 'Active' : 'Inactive'}</span>
            </td>
            <td>
                <small style="color: var(--gray-color);">${service.created_at}</small>
            </td>
            <td>
                <div class="actions">
                    <button class="action-btn edit-btn-small" onclick="editService(${service.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="action-btn delete-btn-small" onclick="deleteServicePrompt(${service.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                    ${service.link ? `<a href="${service.link}" target="_blank" class="action-btn" style="background-color: var(--primary-color);">
                        <i class="fas fa-external-link-alt"></i>
                    </a>` : ''}
                </div>
            </td>
        `;
        serviceListContainer.appendChild(row);
    });
}

// Edit service function
window.editService = async function(id) {
    try {
        const response = await fetch(`${API_BASE_URL}/${id}`);
        const service = await response.json();
        
        if (service) {
            document.getElementById('serviceName').value = service.name;
            document.getElementById('servicePriceDB').value = service.price;
            document.getElementById('serviceFee').value = service.fee;
            document.getElementById('serviceChargeDB').value = service.charge;
            document.getElementById('serviceLink').value = service.link || '';
            document.getElementById('serviceNote').value = service.note || '';
            document.getElementById('serviceStatus').value = service.status;
            serviceIdInput.value = service.id;
            
            serviceFormTitle.textContent = 'Edit Service';
            deleteServiceBtn.classList.remove('hidden');
            serviceFormContainer.classList.remove('hidden');
            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        }
    } catch (error) {
        console.error('Error loading service:', error);
        showNotification('Error loading service. Please try again.', 'error');
    }
};

// Delete service prompt
window.deleteServicePrompt = async function(id) {
    if (confirm('Are you sure you want to delete this service?')) {
        try {
            const response = await fetch(`${API_BASE_URL}/${id}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                loadServices();
                showNotification(result.message, 'success');
            } else {
                showNotification(result.message, 'error');
            }
        } catch (error) {
            console.error('Error deleting service:', error);
            showNotification('Error deleting service. Please try again.', 'error');
        }
    }
};

// Reset form
function resetForm() {
    serviceForm.reset();
    document.getElementById('serviceStatus').value = 'active';
    serviceIdInput.value = '';
}

// Show notification
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        </div>
        <button class="notification-close">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // Add close button functionality
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
        notification.remove();
    });
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Show loading indicator
function showLoading(show) {
    let loadingIndicator = document.getElementById('loadingIndicator');
    
    if (show) {
        if (!loadingIndicator) {
            loadingIndicator = document.createElement('div');
            loadingIndicator.id = 'loadingIndicator';
            loadingIndicator.className = 'spinner';
            serviceListContainer.innerHTML = '';
            serviceListContainer.appendChild(loadingIndicator);
        }
    } else if (loadingIndicator) {
        loadingIndicator.remove();
    }
}

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

// Auto-calculate profit when fee or charge changes
document.getElementById('serviceFee').addEventListener('input', updateProfitDisplay);
document.getElementById('serviceChargeDB').addEventListener('input', updateProfitDisplay);

function updateProfitDisplay() {
    const fee = parseFloat(document.getElementById('serviceFee').value) || 0;
    const charge = parseFloat(document.getElementById('serviceChargeDB').value) || 0;
    const profit = charge - fee;
    
    // Find profit display element or create one
    let profitDisplay = document.getElementById('profitDisplay');
    if (!profitDisplay) {
        profitDisplay = document.createElement('div');
        profitDisplay.id = 'profitDisplay';
        profitDisplay.style.cssText = `
            margin-top: 10px;
            padding: 10px;
            border-radius: 6px;
            font-weight: 600;
            background-color: ${profit >= 0 ? 'rgba(76, 175, 80, 0.1)' : 'rgba(244, 67, 54, 0.1)'};
            color: ${profit >= 0 ? 'var(--success-color)' : 'var(--danger-color)'};
        `;
        document.getElementById('serviceChargeDB').parentNode.appendChild(profitDisplay);
    }
    
    profitDisplay.textContent = `Profit: ₹${profit.toLocaleString('en-IN')}`;
    profitDisplay.style.backgroundColor = profit >= 0 ? 'rgba(76, 175, 80, 0.1)' : 'rgba(244, 67, 54, 0.1)';
    profitDisplay.style.color = profit >= 0 ? 'var(--success-color)' : 'var(--danger-color)';
}

// Initialize the page
document.addEventListener('DOMContentLoaded', () => {
    loadServices();
    
    // Make navigation links active on click
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', function(e) {
            if (this.getAttribute('href') === '#') {
                e.preventDefault();
            }
            document.querySelectorAll('.nav-links a').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            
            // Collapse sidebar on mobile after clicking a link
            if (window.innerWidth < 992) {
                sidebar.classList.add('collapsed');
                sidebarToggle.querySelector('i').className = 'fas fa-bars';
            }
        });
    });
});