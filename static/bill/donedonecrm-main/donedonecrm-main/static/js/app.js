// app.js - Fixed version with working edit and new buttons

class UserManagementSystem {
    constructor() {
        this.currentUser = null;
        this.users = [];
        this.filteredUsers = [];
        this.currentPage = 1;
        this.pageSize = 10;
        this.init();
    }

    async init() {
        console.log('Initializing User Management System...');
        
        // Check authentication
        await this.checkAuth();
        
        // Initialize UI components
        this.initSidebar();
        this.initEventListeners();
        
        // Load initial data
        await this.loadUsers();
        await this.loadStats();
    }

    async checkAuth() {
        console.log('Checking authentication...');
        
        try {
            // Try to get current user from localStorage
            const savedUser = localStorage.getItem('currentUser');
            if (savedUser) {
                this.currentUser = JSON.parse(savedUser);
                console.log('User found in localStorage:', this.currentUser);
            } else {
                // For demo, create a mock admin user
                this.currentUser = {
                    id: 1,
                    username: 'admin',
                    role: 'admin',
                    name: 'Administrator'
                };
                localStorage.setItem('currentUser', JSON.stringify(this.currentUser));
                console.log('Created demo admin user:', this.currentUser);
            }
            
            // Update UI with user info
            this.updateUserInfo();
            
        } catch (error) {
            console.error('Auth error:', error);
            this.showNotification('Authentication error', 'error');
        }
    }

    updateUserInfo() {
        const usernameEl = document.getElementById('sidebarUsername');
        const roleEl = document.getElementById('sidebarRole');
        
        if (usernameEl && roleEl && this.currentUser) {
            usernameEl.textContent = this.currentUser.name || this.currentUser.username;
            roleEl.textContent = this.currentUser.role;
            
            // Update role badge color
            roleEl.className = 'user-role-sidebar';
            roleEl.classList.add(`role-${this.currentUser.role}`);
        }
    }

    initSidebar() {
        console.log('Initializing sidebar...');
        
        const sidebar = document.getElementById('sidebar');
        const sidebarToggle = document.getElementById('sidebarToggle');
        const mobileMenuToggle = document.getElementById('mobileMenuToggle');

        // Mobile menu toggle
        mobileMenuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('active');
        });

        // Close sidebar on mobile
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.remove('active');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 && 
                !sidebar.contains(e.target) && 
                !mobileMenuToggle.contains(e.target) && 
                sidebar.classList.contains('active')) {
                sidebar.classList.remove('active');
            }
        });

        // Navigation links
        const navLinks = document.querySelectorAll('.nav-links a');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                if (link.getAttribute('href') === '#') {
                    e.preventDefault();
                    navLinks.forEach(l => l.classList.remove('active'));
                    link.classList.add('active');
                }
            });
        });
    }

    initEventListeners() {
        console.log('Initializing event listeners...');
        
        // Main buttons
        document.getElementById('addUserBtn').addEventListener('click', () => this.openAddUserModal());
        document.getElementById('refreshUsersBtn').addEventListener('click', () => this.loadUsers());
        document.getElementById('closeUserModal').addEventListener('click', () => this.closeModal());
        document.getElementById('cancelUserBtn').addEventListener('click', () => this.closeModal());
        document.getElementById('saveUserBtn').addEventListener('click', () => this.saveUser());
        document.getElementById('resetFormBtn').addEventListener('click', () => this.resetForm());
        
        // Modal close on outside click
        const modal = document.getElementById('userManagementModal');
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeModal();
            }
        });
        
        // Delete modal
        document.getElementById('closeDeleteModal').addEventListener('click', () => this.closeDeleteModal());
        document.getElementById('cancelDeleteBtn').addEventListener('click', () => this.closeDeleteModal());
        document.getElementById('confirmDeleteBtn').addEventListener('click', () => this.deleteConfirmed());
        
        // Search and filter
        document.getElementById('searchUsers').addEventListener('input', (e) => {
            this.filterUsers(e.target.value);
        });
        
        document.getElementById('filterRole').addEventListener('change', (e) => {
            this.filterByRole(e.target.value);
        });
        
        document.getElementById('clearFiltersBtn').addEventListener('click', () => {
            document.getElementById('searchUsers').value = '';
            document.getElementById('filterRole').value = '';
            this.filterUsers('');
        });
        
        // Pagination
        document.getElementById('prevPage').addEventListener('click', () => this.prevPage());
        document.getElementById('nextPage').addEventListener('click', () => this.nextPage());
        
        console.log('Event listeners initialized');
    }

    async loadUsers() {
        console.log('Loading users...');
        
        try {
            // Show loading
            const tbody = document.getElementById('userTableBody');
            tbody.innerHTML = `
                <tr id="loadingRow">
                    <td colspan="7" style="text-align: center; padding: 40px;">
                        <div class="spinner"></div>
                        <p>Loading users...</p>
                    </td>
                </tr>
            `;
            
            const response = await fetch('/api/users');
            if (!response.ok) throw new Error('Failed to load users');
            
            this.users = await response.json();
            this.filteredUsers = [...this.users];
            console.log(`Loaded ${this.users.length} users`);
            
            this.renderUserTable();
            this.renderUserList();
            
            this.showNotification(`Loaded ${this.users.length} users successfully`, 'success');
            
        } catch (error) {
            console.error('Error loading users:', error);
            
            const tbody = document.getElementById('userTableBody');
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 40px; color: #dc3545;">
                        <i class="fas fa-exclamation-triangle" style="font-size: 48px; margin-bottom: 20px;"></i>
                        <p>Error loading users</p>
                        <p style="font-size: 12px;">${error.message}</p>
                        <button onclick="window.userSystem.loadUsers()" class="btn btn-small" style="margin-top: 10px;">
                            <i class="fas fa-redo"></i> Retry
                        </button>
                    </td>
                </tr>
            `;
            
            this.showNotification('Failed to load users', 'error');
        }
    }

    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            if (response.ok) {
                const stats = await response.json();
                console.log('Statistics loaded:', stats);
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    renderUserTable() {
        console.log('Rendering user table...');
        
        const tbody = document.getElementById('userTableBody');
        tbody.innerHTML = '';

        if (this.filteredUsers.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 40px;">
                        <i class="fas fa-users" style="font-size: 48px; color: #ddd; margin-bottom: 20px;"></i>
                        <p>No users found</p>
                    </td>
                </tr>
            `;
            this.hidePagination();
            return;
        }

        // Calculate pagination
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = Math.min(startIndex + this.pageSize, this.filteredUsers.length);
        const pageUsers = this.filteredUsers.slice(startIndex, endIndex);

        pageUsers.forEach(user => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${user.id}</td>
                <td><strong>${user.name || user.username}</strong></td>
                <td>${user.username}</td>
                <td>${user.email || 'N/A'}</td>
                <td>
                    <span class="role-badge role-${user.role}">
                        ${user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                    </span>
                </td>
                <td>${user.mobile_number || 'N/A'}</td>
                <td>
                    <div class="action-buttons">
                        ${this.canEditUser(user) ? `
                            <button class="btn-icon edit-btn" data-id="${user.id}" title="Edit User">
                                <i class="fas fa-edit"></i>
                            </button>
                        ` : ''}
                        ${this.canDeleteUser(user) ? `
                            <button class="btn-icon delete-btn" data-id="${user.id}" title="Delete User">
                                <i class="fas fa-trash"></i>
                            </button>
                        ` : ''}
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });

        // Add event listeners to buttons
        this.attachTableButtonListeners();
        
        // Update pagination
        this.updatePagination();
    }

    attachTableButtonListeners() {
        // Edit buttons
        document.querySelectorAll('.edit-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const userId = parseInt(e.currentTarget.getAttribute('data-id'));
                console.log('Edit button clicked for user ID:', userId);
                this.openEditUserModal(userId);
            });
        });

        // Delete buttons
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const userId = parseInt(e.currentTarget.getAttribute('data-id'));
                console.log('Delete button clicked for user ID:', userId);
                this.confirmDeleteUser(userId);
            });
        });
        
        // Make rows clickable for edit
        document.querySelectorAll('#userTableBody tr').forEach(row => {
            const editBtn = row.querySelector('.edit-btn');
            if (editBtn) {
                const userId = parseInt(editBtn.getAttribute('data-id'));
                row.style.cursor = 'pointer';
                row.addEventListener('click', (e) => {
                    if (!e.target.closest('.action-buttons')) {
                        this.openEditUserModal(userId);
                    }
                });
            }
        });
    }

    renderUserList() {
        const container = document.getElementById('userListContainer');
        if (!container) return;
        
        container.innerHTML = '';

        this.users.slice(0, 20).forEach(user => {
            const userItem = document.createElement('div');
            userItem.className = 'user-item';
            userItem.innerHTML = `
                <div class="user-info">
                    <h5>${user.name || user.username}</h5>
                    <p>${user.email || 'No email'}</p>
                </div>
                <div class="user-role">
                    <span class="role-badge role-${user.role}">${user.role}</span>
                </div>
            `;
            userItem.addEventListener('click', () => {
                this.openEditUserModal(user.id);
            });
            container.appendChild(userItem);
        });
    }

    canEditUser(user) {
        // Only admin and manager can edit
        // Managers can only edit staff users
        if (this.currentUser.role === 'admin') return true;
        if (this.currentUser.role === 'manager' && user.role === 'staff') return true;
        return false;
    }

    canDeleteUser(user) {
        // Only admin can delete users
        // Cannot delete yourself
        return this.currentUser.role === 'admin' && user.id !== this.currentUser.id;
    }

    filterUsers(searchTerm) {
        searchTerm = searchTerm.toLowerCase();
        this.filteredUsers = this.users.filter(user => {
            return (
                (user.username && user.username.toLowerCase().includes(searchTerm)) ||
                (user.email && user.email.toLowerCase().includes(searchTerm)) ||
                (user.name && user.name.toLowerCase().includes(searchTerm)) ||
                (user.mobile_number && user.mobile_number.includes(searchTerm))
            );
        });
        this.currentPage = 1;
        this.renderUserTable();
    }

    filterByRole(role) {
        if (!role) {
            this.filteredUsers = [...this.users];
        } else {
            this.filteredUsers = this.users.filter(user => user.role === role);
        }
        this.currentPage = 1;
        this.renderUserTable();
    }

    updatePagination() {
        const totalPages = Math.ceil(this.filteredUsers.length / this.pageSize);
        
        if (totalPages <= 1) {
            this.hidePagination();
            return;
        }
        
        const pageInfo = document.getElementById('pageInfo');
        const prevBtn = document.getElementById('prevPage');
        const nextBtn = document.getElementById('nextPage');
        const pagination = document.getElementById('pagination');
        
        pageInfo.textContent = `Page ${this.currentPage} of ${totalPages}`;
        prevBtn.disabled = this.currentPage === 1;
        nextBtn.disabled = this.currentPage === totalPages;
        
        pagination.style.display = 'block';
    }

    hidePagination() {
        document.getElementById('pagination').style.display = 'none';
    }

    prevPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.renderUserTable();
        }
    }

    nextPage() {
        const totalPages = Math.ceil(this.filteredUsers.length / this.pageSize);
        if (this.currentPage < totalPages) {
            this.currentPage++;
            this.renderUserTable();
        }
    }

    openAddUserModal() {
        console.log('Opening add user modal...');
        this.resetForm();
        document.getElementById('userFormTitle').textContent = 'Add New User';
        document.getElementById('modalTitle').textContent = 'Add New User';
        
        // Only admins can create admin users
        const roleInput = document.getElementById('userRole');
        if (this.currentUser.role !== 'admin') {
            roleInput.value = 'staff';
            roleInput.disabled = true;
        } else {
            roleInput.disabled = false;
        }
        
        document.getElementById('userManagementModal').style.display = 'flex';
        
        // Focus on username field
        setTimeout(() => {
            document.getElementById('userUsername').focus();
        }, 100);
    }

    async openEditUserModal(userId) {
        console.log('Opening edit user modal for ID:', userId);
        
        try {
            const response = await fetch(`/api/users/${userId}`);
            if (!response.ok) throw new Error('Failed to load user');
            
            const user = await response.json();
            console.log('Loaded user data:', user);
            
            // Check if current user can edit this user
            if (!this.canEditUser(user)) {
                this.showNotification('You do not have permission to edit this user', 'error');
                return;
            }
            
            this.resetForm();
            document.getElementById('userFormTitle').textContent = 'Edit User';
            document.getElementById('modalTitle').textContent = 'Edit User';
            
            // Fill form with user data
            document.getElementById('userId').value = user.id;
            document.getElementById('userUsername').value = user.username;
            document.getElementById('Username').value = user.name || '';
            document.getElementById('fathername').value = user.father_name || '';
            document.getElementById('mothername').value = user.mother_name || '';
            document.getElementById('dateofbirth').value = user.date_of_birth || '';
            document.getElementById('userEmail').value = user.email || '';
            document.getElementById('userRole').value = user.role;
            document.getElementById('usernumber').value = user.mobile_number || '';
            document.getElementById('useremer').value = user.emergency_contact || '';
            document.getElementById('useraadhar').value = user.aadhar_number || '';
            document.getElementById('userpan').value = user.pan_number || '';
            document.getElementById('permanentadd').value = user.permanent_address || '';
            document.getElementById('presentadd').value = user.present_address || '';
            document.getElementById('dateofjoining').value = user.date_of_joining || '';
            document.getElementById('userpromotion').value = user.first_promotion_date || '';
            
            // Disable role field for non-admins
            if (this.currentUser.role !== 'admin') {
                document.getElementById('userRole').disabled = true;
            }
            
            document.getElementById('userManagementModal').style.display = 'flex';
            
            // Focus on first field
            setTimeout(() => {
                document.getElementById('userUsername').focus();
            }, 100);
            
        } catch (error) {
            console.error('Error loading user:', error);
            this.showNotification('Failed to load user data', 'error');
        }
    }

    closeModal() {
        document.getElementById('userManagementModal').style.display = 'none';
        this.resetForm();
    }

    resetForm() {
        document.getElementById('userForm').reset();
        document.getElementById('userId').value = '';
        document.getElementById('userRole').disabled = false;
        
        // Clear error messages
        document.querySelectorAll('.error-message').forEach(el => {
            el.textContent = '';
            el.style.display = 'none';
        });
        
        // Clear error classes
        document.querySelectorAll('.form-control').forEach(el => {
            el.classList.remove('error', 'success');
        });
    }

    validateForm() {
        let isValid = true;
        
        // Clear previous errors
        document.querySelectorAll('.error-message').forEach(el => {
            el.textContent = '';
            el.style.display = 'none';
        });
        
        document.querySelectorAll('.form-control').forEach(el => {
            el.classList.remove('error', 'success');
        });
        
        // Validate required fields
        const requiredFields = [
            { id: 'userUsername', name: 'Username', errorId: 'usernameError' },
            { id: 'userEmail', name: 'Email', errorId: 'emailError' },
            { id: 'Username', name: 'Full Name', errorId: 'nameError' },
            { id: 'userRole', name: 'Role', errorId: 'roleError' },
            { id: 'usernumber', name: 'Mobile Number', errorId: 'mobileError' }
        ];
        
        requiredFields.forEach(field => {
            const input = document.getElementById(field.id);
            const errorEl = document.getElementById(field.errorId);
            
            if (!input.value.trim()) {
                isValid = false;
                input.classList.add('error');
                errorEl.textContent = `${field.name} is required`;
                errorEl.style.display = 'block';
            } else {
                input.classList.add('success');
            }
            
            // Validate email format
            if (field.id === 'userEmail' && input.value.trim()) {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(input.value)) {
                    isValid = false;
                    input.classList.add('error');
                    errorEl.textContent = 'Please enter a valid email address';
                    errorEl.style.display = 'block';
                }
            }
        });
        
        // Validate password for new user
        const userId = document.getElementById('userId').value;
        const password = document.getElementById('userPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        if (!userId && !password) {
            isValid = false;
            const passwordInput = document.getElementById('userPassword');
            const errorEl = document.getElementById('passwordError');
            passwordInput.classList.add('error');
            errorEl.textContent = 'Password is required for new users';
            errorEl.style.display = 'block';
        }
        
        if (password && password !== confirmPassword) {
            isValid = false;
            const confirmInput = document.getElementById('confirmPassword');
            const errorEl = document.getElementById('confirmPasswordError');
            confirmInput.classList.add('error');
            errorEl.textContent = 'Passwords do not match';
            errorEl.style.display = 'block';
        }
        
        return isValid;
    }

    async saveUser() {
        console.log('Saving user...');
        
        if (!this.validateForm()) {
            this.showNotification('Please fix the errors in the form', 'error');
            return;
        }
        
        const userId = document.getElementById('userId').value;
        const isEditMode = !!userId;
        
        const userData = {
            username: document.getElementById('userUsername').value.trim(),
            name: document.getElementById('Username').value.trim(),
            father_name: document.getElementById('fathername').value.trim(),
            mother_name: document.getElementById('mothername').value.trim(),
            date_of_birth: document.getElementById('dateofbirth').value,
            email: document.getElementById('userEmail').value.trim(),
            role: document.getElementById('userRole').value,
            mobile_number: document.getElementById('usernumber').value.trim(),
            emergency_contact: document.getElementById('useremer').value.trim(),
            aadhar_number: document.getElementById('useraadhar').value.trim(),
            pan_number: document.getElementById('userpan').value.trim(),
            permanent_address: document.getElementById('permanentadd').value.trim(),
            present_address: document.getElementById('presentadd').value.trim(),
            date_of_joining: document.getElementById('dateofjoining').value,
            first_promotion_date: document.getElementById('userpromotion').value
        };

        // Add password if provided
        const password = document.getElementById('userPassword').value;
        if (password) {
            userData.password = password;
        }

        try {
            const url = isEditMode ? `/api/users/${userId}` : '/api/users';
            const method = isEditMode ? 'PUT' : 'POST';

            console.log(`Saving user with ${method} to ${url}`, userData);

            // Show loading
            const saveBtn = document.getElementById('saveUserBtn');
            const originalText = saveBtn.innerHTML;
            saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
            saveBtn.disabled = true;

            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to save user');
            }

            const result = await response.json();
            console.log('User saved successfully:', result);
            
            this.showNotification(
                isEditMode ? 'User updated successfully!' : 'User created successfully!',
                'success'
            );
            
            this.closeModal();
            await this.loadUsers();

        } catch (error) {
            console.error('Error saving user:', error);
            this.showNotification(`Error: ${error.message}`, 'error');
            
            // Reset save button
            const saveBtn = document.getElementById('saveUserBtn');
            saveBtn.innerHTML = '<i class="fas fa-save"></i> Save User';
            saveBtn.disabled = false;
        }
    }

    confirmDeleteUser(userId) {
        const user = this.users.find(u => u.id === userId);
        if (!user) return;

        if (!this.canDeleteUser(user)) {
            this.showNotification('You do not have permission to delete this user', 'error');
            return;
        }

        this.userToDelete = user;
        document.getElementById('deleteMessage').textContent = 
            `Are you sure you want to delete user "${user.name || user.username}"? This action cannot be undone.`;
        document.getElementById('deleteConfirmationModal').style.display = 'flex';
    }

    closeDeleteModal() {
        document.getElementById('deleteConfirmationModal').style.display = 'none';
        this.userToDelete = null;
    }

    async deleteConfirmed() {
        if (!this.userToDelete) return;

        try {
            const response = await fetch(`/api/users/${this.userToDelete.id}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to delete user');
            }

            this.showNotification('User deleted successfully!', 'success');
            this.closeDeleteModal();
            await this.loadUsers();

        } catch (error) {
            console.error('Error deleting user:', error);
            this.showNotification(`Error: ${error.message}`, 'error');
        }
    }

    showNotification(message, type = 'info') {
        console.log(`Notification [${type}]: ${message}`);
        
        // Remove existing notifications
        const existingNotifications = document.querySelectorAll('.notification');
        existingNotifications.forEach(notification => {
            notification.remove();
        });

        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        
        const icon = type === 'success' ? 'check-circle' : 
                    type === 'error' ? 'exclamation-circle' : 
                    type === 'warning' ? 'exclamation-triangle' : 'info-circle';
        
        notification.innerHTML = `
            <i class="fas fa-${icon}"></i>
            <span>${message}</span>
            <button class="notification-close">&times;</button>
        `;

        // Add styles
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background-color: ${type === 'success' ? '#28a745' : 
                             type === 'error' ? '#dc3545' : 
                             type === 'warning' ? '#ffc107' : '#17a2b8'};
            color: white;
            border-radius: 5px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 300px;
            max-width: 500px;
            animation: slideIn 0.3s ease-out;
        `;

        // Add close button styles
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.style.cssText = `
            background: none;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            padding: 0;
            margin-left: auto;
            opacity: 0.8;
            transition: opacity 0.2s;
        `;

        closeBtn.addEventListener('click', () => {
            notification.style.animation = 'slideOut 0.3s ease-out forwards';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        });

        // Add animations
        const style = document.createElement('style');
        if (!document.querySelector('#notification-styles')) {
            style.id = 'notification-styles';
            style.textContent = `
                @keyframes slideIn {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                @keyframes slideOut {
                    from {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    to {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.animation = 'slideOut 0.3s ease-out forwards';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.remove();
                    }
                }, 300);
            }
        }, 5000);

        document.body.appendChild(notification);
    }

    // Export users to CSV
    exportToCSV() {
        if (this.users.length === 0) {
            this.showNotification('No users to export', 'warning');
            return;
        }

        const headers = ['ID', 'Username', 'Name', 'Email', 'Role', 'Mobile', 'Joining Date'];
        const csvData = [
            headers.join(','),
            ...this.users.map(user => [
                user.id,
                `"${user.username}"`,
                `"${user.name || ''}"`,
                `"${user.email || ''}"`,
                user.role,
                `"${user.mobile_number || ''}"`,
                `"${user.date_of_joining || ''}"`
            ].join(','))
        ].join('\n');

        const blob = new Blob([csvData], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `users_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        this.showNotification('Users exported to CSV successfully', 'success');
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing application...');
    window.userSystem = new UserManagementSystem();
    
    // Add export button
    const dashboardHeader = document.querySelector('.dashboard-header');
    const exportBtn = document.createElement('button');
    exportBtn.className = 'btn btn-success';
    exportBtn.innerHTML = '<i class="fas fa-file-export"></i> Export CSV';
    exportBtn.style.marginLeft = '10px';
    exportBtn.addEventListener('click', () => {
        window.userSystem.exportToCSV();
    });
    
    dashboardHeader.appendChild(exportBtn);
    
    console.log('Application initialized');
});

// Add global helper functions
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

function truncateText(text, maxLength = 50) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl + F for search
    if (e.ctrlKey && e.key === 'f') {
        e.preventDefault();
        const searchInput = document.getElementById('searchUsers');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }
    
    // Escape to close modal
    if (e.key === 'Escape') {
        const modal = document.getElementById('userManagementModal');
        if (modal && modal.style.display === 'flex') {
            window.userSystem.closeModal();
        }
        
        const deleteModal = document.getElementById('deleteConfirmationModal');
        if (deleteModal && deleteModal.style.display === 'flex') {
            window.userSystem.closeDeleteModal();
        }
    }
    
    // Ctrl + N for new user
    if (e.ctrlKey && e.key === 'n') {
        e.preventDefault();
        const modal = document.getElementById('userManagementModal');
        if (!modal || modal.style.display === 'none') {
            window.userSystem.openAddUserModal();
        }
    }
});