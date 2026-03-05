

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


        // ========== GLOBAL VARIABLES ==========
        let isSelfPayCompletionActive = false;
        let tasks = [];

        let currentTab = 'today';
        let selectedService = null;
        let servicesData = [];
        let currentTaskId = null;
        let staffMembers = [];
        let openplaceNotifications = 0;

        // Helper for authenticated fetch requests (include session cookies)
        async function apiFetch(url, options = {}) {
            options = options || {};
            if (!options.credentials) options.credentials = 'same-origin';
            return fetch(url, options);
        }

        // ========== USER PERMISSION FUNCTIONS ==========
        function canUserDeleteTask() {
            const userRole = document.getElementById('currentUserRole').value;
            return userRole === 'admin'; // Only admins can delete
        }

        function canUserCancelTask() {
            const userRole = document.getElementById('currentUserRole').value;
            return ['staff', 'manager', 'admin'].includes(userRole);
        }

        // Resilient tab switcher — usable from inline onclick attributes
        function switchTab(tab) {
            currentTab = tab;
            // Update top nav tabs
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));

            // Update sidebar active link if present
            document.querySelectorAll('.nav-links a').forEach(a => {
                const aTab = a.dataset.tab;
                a.classList.toggle('active', aTab === tab);
            });

            // Show/hide open place filters
            const openplaceFilters = document.getElementById('openplaceFilters');
            if (openplaceFilters) {
                openplaceFilters.style.display = tab === 'openplace' ? 'block' : 'none';
            }

            updateTableTitle();
            loadTasks();
        }

        // ========== INPUT VALIDATION FUNCTIONS ==========
        function validatePhoneInput(input) {
            const phone = input.value.trim();
            const phoneError = document.getElementById('phoneError');

            // Remove non-digits
            input.value = phone.replace(/\D/g, '');

            // Validate: exactly 10 digits
            if (input.value.length > 0 && input.value.length !== 10) {
                phoneError.textContent = 'Phone number must be exactly 10 digits';
                phoneError.style.display = 'block';
                input.setCustomValidity('Phone number must be exactly 10 digits');
                return false;
            } else if (input.value.length === 10) {
                phoneError.style.display = 'none';
                input.setCustomValidity('');
                return true;
            } else {
                phoneError.style.display = 'none';
                input.setCustomValidity('');
                return true; // Empty is OK (will be caught by required)
            }
        }

        function validateNameInput(input) {
            const name = input.value;
            const nameError = document.getElementById('nameError');

            // Pattern: only letters, spaces, dots, hyphens, apostrophes
            const validNamePattern = /^[a-zA-Z\s.\-']+$/;
            // Emoji detection (basic ranges)
            const emojiPattern = /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2702}-\u{27B0}\u{24C2}-\u{1F251}]/u;

            if (name.length > 0) {
                if (emojiPattern.test(name)) {
                    nameError.textContent = 'Emojis are not allowed in customer name';
                    nameError.style.display = 'block';
                    input.setCustomValidity('Emojis are not allowed');
                    return false;
                } else if (!validNamePattern.test(name)) {
                    nameError.textContent = 'Only letters, spaces, dots, hyphens, and apostrophes allowed';
                    nameError.style.display = 'block';
                    input.setCustomValidity('Invalid characters in name');
                    return false;
                } else {
                    nameError.style.display = 'none';
                    input.setCustomValidity('');
                    return true;
                }
            } else {
                nameError.style.display = 'none';
                input.setCustomValidity('');
                return true; // Empty is OK (will be caught by required)
            }
        }

        // ========== EXTRA CHARGES HELPER ==========
        function toggleExtraCharge(checkbox, inputId) {
            const input = document.getElementById(inputId);
            if (input) {
                input.disabled = !checkbox.checked;
                if (!checkbox.checked) {
                    input.value = ''; // Clear value when unchecked
                }
            }
        }

        // ========== COMPLETION AMOUNT CALCULATION ==========
        function calculateCompletionAmounts() {
            const collected = parseFloat(document.getElementById('collectedAmount')?.value) || 0;
            const totalAmount = parseFloat(document.getElementById('taskAmount')?.value) || 0;
            const alreadyPaid = parseFloat(document.getElementById('paidAmount')?.value) || 0;

            // Calculate what's due: total - already paid
            const remaining = totalAmount - alreadyPaid;

            // Update due amount display
            const dueAmountField = document.getElementById('dueAmount');
            if (dueAmountField) {
                dueAmountField.value = Math.max(0, remaining - collected).toFixed(2);
            }

            console.log('Completion calculation:', {
                totalAmount,
                alreadyPaid,
                collected,
                remaining,
                finalDue: Math.max(0, remaining - collected)
            });
        }

        // ========== INITIALIZATION ==========
        document.addEventListener('DOMContentLoaded', function () {
            initApplication();
            setupRoleBasedUI();
        });

        function setupRoleBasedUI() {
            const userRole = document.getElementById('currentUserRole').value;

            // Hide "All Tasks" tab if not admin/manager
            if (!['admin', 'manager'].includes(userRole)) {
                const allTasksTab = document.querySelector('[data-tab="all"]');
                if (allTasksTab) {
                    allTasksTab.style.display = 'none';
                }
            }

            // Change checkout button for admin
            if (userRole === 'admin' || userRole === 'administrator') {
                const checkoutBtn = document.getElementById('checkoutBtn');
                const checkoutBtnText = document.getElementById('checkoutBtnText');
                const checkoutIcon = checkoutBtn.querySelector('i');

                if (checkoutBtn) {
                    checkoutBtn.href = '/users';
                    checkoutBtnText.textContent = 'Back to Admin';
                    if (checkoutIcon) {
                        checkoutIcon.className = 'fas fa-arrow-left';
                    }
                }
            }

            // Update table titles based on role
            updateTableTitle();
        }

        function initApplication() {
            initModals();
            initSidebar();
            initEventListeners();
            loadStatistics();
            loadTasks();
            updateUserInfo();
            loadStaffMembers();
            checkOpenPlaceNotifications();
            initFormEvents();
            loadBranches();
            setupInitialTab();
        }

        function setupInitialTab() {
            // Check if there's an initial tab specified in the template
            const urlParams = new URLSearchParams(window.location.search);
            const initialTab = urlParams.get('tab') || '{{ initial_tab or "today" }}';

            if (initialTab && initialTab !== 'today') {
                // Find and click the corresponding tab
                const tabButton = document.querySelector(`[data-tab="${initialTab}"]`);
                if (tabButton) {
                    tabButton.click();
                }
            }
        }

        // ========== MODAL MANAGEMENT ==========
        function initModals() {
            // Add event listeners for all close buttons (×)
            document.querySelectorAll('.close-modal').forEach(button => {
                button.addEventListener('click', function () {
                    const modal = this.closest('.modal');
                    if (modal) {
                        closeModal(modal.id);
                    }
                });
            });

            // Add event listeners for cancel buttons
            document.querySelectorAll('.btn-secondary').forEach(button => {
                if (button.id.includes('cancel') || button.textContent.includes('Cancel')) {
                    button.addEventListener('click', function () {
                        const modal = this.closest('.modal');
                        if (modal) {
                            closeModal(modal.id);
                        }
                    });
                }
            });

            // Specific modal close buttons
            const closeButtons = [
                'cancelTaskBtn',
                'closeNewTaskModal',
                'closeTaskDetailsModal',
                'closeDetailsBtn',
                'closeCompleteModal',
                'cancelCompleteBtn',
                'closeHoldModal',
                'cancelHoldBtn',
                'closeStatusModal',
                'cancelStatusBtn',
                'closeStaffAssignmentModal',
                'cancelStaffAssignmentBtn',
                'closeTakeTaskModal',
                'cancelTakeTaskBtn',
                'closeEditTaskModal',
                'cancelEditBtn'
            ];

            closeButtons.forEach(buttonId => {
                const button = document.getElementById(buttonId);
                if (button) {
                    button.addEventListener('click', function () {
                        const modal = this.closest('.modal');
                        if (modal) {
                            closeModal(modal.id);
                        }
                    });
                }
            });

            // Close modals when clicking outside
            document.querySelectorAll('.modal').forEach(modal => {
                modal.addEventListener('click', function (e) {
                    if (e.target === this) {
                        closeModal(this.id);
                    }
                });
            });
        }

        function showModal(modalId) {
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.style.display = 'flex';
                document.body.style.overflow = 'hidden';
            }
        }

        function closeModal(modalId) {
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.style.display = 'none';
                document.body.style.overflow = 'auto';

                // Reset form if it's the new task modal
                if (modalId === 'newTaskModal') {
                    resetNewTaskForm();
                }
                // Reset form if it's the edit task modal
                if (modalId === 'editTaskModal') {
                    resetEditTaskForm();
                }
            }
        }

        // ========== SIDEBAR MANAGEMENT ==========
        function initSidebar() {
            const sidebar = document.getElementById('sidebar');
            const sidebarToggle = document.getElementById('sidebarToggle');
            const mobileNavToggle = document.getElementById('mobileNavToggle');
            const logoutBtn = document.getElementById('logoutBtn');

            if (!sidebar || !sidebarToggle || !mobileNavToggle || !logoutBtn) {
                console.error('Sidebar elements not found');
                return;
            }

            // Desktop sidebar toggle
            sidebarToggle.addEventListener('click', () => {
                sidebar.classList.toggle('collapsed');
                const icon = sidebarToggle.querySelector('i');
                if (icon) {
                    icon.className = sidebar.classList.contains('collapsed') ? 'fas fa-bars' : 'fas fa-times';
                }
            });

            // Mobile sidebar toggle
            mobileNavToggle.addEventListener('click', () => {
                sidebar.classList.toggle('active');
            });

            // Logout button
            logoutBtn.addEventListener('click', () => {
                if (confirm('Are you sure you want to logout?')) {
                    window.location.href = '/logout';
                }
            });

            // Close sidebar when clicking outside on mobile
            document.addEventListener('click', (e) => {
                if (window.innerWidth <= 1200 &&
                    sidebar.classList.contains('active') &&
                    !sidebar.contains(e.target) &&
                    e.target !== mobileNavToggle &&
                    !mobileNavToggle.contains(e.target)) {
                    sidebar.classList.remove('active');
                }
            });
        }

        // ========== EVENT LISTENERS ==========
        function initEventListeners() {
            // Navigation tabs
            document.querySelectorAll('.nav-tab').forEach(tab => {
                tab.addEventListener('click', function () {
                    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
                    this.classList.add('active');
                    currentTab = this.dataset.tab;

                    // Show/hide open place filters
                    const openplaceFilters = document.getElementById('openplaceFilters');
                    if (openplaceFilters) {
                        openplaceFilters.style.display = currentTab === 'openplace' ? 'block' : 'none';
                    }

                    updateTableTitle();
                    loadTasks();
                });
            });

            // Open Place filter buttons
            document.querySelectorAll('.openplace-filter-btn').forEach(btn => {
                btn.addEventListener('click', function () {
                    document.querySelectorAll('.openplace-filter-btn').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');

                    if (currentTab === 'openplace') {
                        loadOpenPlaceTasks(this.dataset.filter);
                    }
                });
            });

            // Search input
            const taskSearch = document.getElementById('taskSearch');
            if (taskSearch) {
                taskSearch.addEventListener('input', searchTasks);
            }

            // Action buttons
            const actionButtons = ['newTaskBtn', 'createFirstTaskBtn'];
            actionButtons.forEach(btnId => {
                const btn = document.getElementById(btnId);
                if (btn) {
                    btn.addEventListener('click', showNewTaskModal);
                }
            });

            // Filter button
            const filterBtn = document.getElementById('filterBtn');
            if (filterBtn) {
                filterBtn.addEventListener('click', showFilterOptions);
            }

            // Status change modal
            const newStatusSelect = document.getElementById('newStatus');
            if (newStatusSelect) {
                newStatusSelect.addEventListener('change', handleStatusChange);
            }

            // Hold modal buttons
            const confirmHoldBtn = document.getElementById('confirmHoldBtn');
            if (confirmHoldBtn) {
                confirmHoldBtn.addEventListener('click', confirmHoldTask);
            }

            // Status change modal buttons
            const confirmStatusBtn = document.getElementById('confirmStatusBtn');
            if (confirmStatusBtn) {
                confirmStatusBtn.addEventListener('click', confirmStatusChange);
            }

            // Submit task
            const submitBtn = document.getElementById('submitTaskBtn');
            if (submitBtn) {
                submitBtn.addEventListener('click', submitTask);
            }

            // Update task button
            const updateTaskBtn = document.getElementById('updateTaskBtn');
            if (updateTaskBtn) {
                updateTaskBtn.addEventListener('click', updateTask);
            }

            // Complete task modal
            const confirmCompleteBtn = document.getElementById('confirmCompleteBtn');
            if (confirmCompleteBtn) {
                confirmCompleteBtn.addEventListener('click', completeTask);
            }
            // Due reason type: show offer amount field when "Offer" is selected
            document.querySelectorAll('input[name="completeDueReason"]').forEach(function (radio) {
                radio.addEventListener('change', function () {
                    const sec = document.getElementById('completeOfferDetailsSection');
                    const amt = document.getElementById('completeOfferAmount');
                    if (sec && amt) {
                        sec.style.display = this.value === 'offer' ? 'block' : 'none';
                        amt.required = this.value === 'offer';
                    }
                });
            });

            // Edit task button in task details modal
            const editTaskBtn = document.getElementById('editTaskBtn');
            if (editTaskBtn) {
                editTaskBtn.addEventListener('click', function () {
                    if (currentTaskId) {
                        editTask(currentTaskId);
                        closeModal('taskDetailsModal');
                    }
                });
            }

            // Send to Open Place button in task details
            const sendToOpenPlaceBtn = document.getElementById('sendToOpenPlaceBtn');
            if (sendToOpenPlaceBtn) {
                sendToOpenPlaceBtn.addEventListener('click', function () {
                    if (currentTaskId) {
                        sendTaskToOpenPlace(currentTaskId);
                    }
                });
            }

            // Staff assignment modal buttons
            const confirmStaffAssignmentBtn = document.getElementById('confirmStaffAssignmentBtn');
            if (confirmStaffAssignmentBtn) {
                confirmStaffAssignmentBtn.addEventListener('click', confirmStaffAssignment);
            }

            // Take task modal buttons
            const confirmTakeTaskBtn = document.getElementById('confirmTakeTaskBtn');
            if (confirmTakeTaskBtn) {
                confirmTakeTaskBtn.addEventListener('click', confirmTakeTask);
            }

            // Payment mode change
            const paymentModeSelect = document.getElementById('paymentMode');
            if (paymentModeSelect) {
                paymentModeSelect.addEventListener('change', updateSelfPayFields);
            }
            const firstPaymentModeSelect = document.getElementById('firstPaymentMode');
            if (firstPaymentModeSelect) {
                firstPaymentModeSelect.addEventListener('change', updateSelfPayFields);
            }
            const secondPaymentModeSelect = document.getElementById('secondPaymentMode');
            if (secondPaymentModeSelect) {
                secondPaymentModeSelect.addEventListener('change', updateSelfPayFields);
            }

            // Payment mode change listener for complete task modal
            const duePaymentMode = document.getElementById('duePaymentMode');
            if (duePaymentMode) {
                duePaymentMode.addEventListener('change', handleDuePaymentModeChange);
            }

            const statusPaymentMode = document.getElementById('statusPaymentMode');
            if (statusPaymentMode) {
                statusPaymentMode.addEventListener('change', handleStatusPaymentModeChange);
            }

            // Hybrid payment input listeners
            const hybridOnlineAmount = document.getElementById('hybridOnlineAmount');
            const hybridCashAmount = document.getElementById('hybridCashAmount');
            if (hybridOnlineAmount) {
                hybridOnlineAmount.addEventListener('input', validateHybridPayment);
            }
            if (hybridCashAmount) {
                hybridCashAmount.addEventListener('input', validateHybridPayment);
            }

            // Extra charges checkboxes
            document.querySelectorAll('input[name="completeExtraCharges"]').forEach(checkbox => {
                checkbox.addEventListener('change', toggleExtraChargeAmount);
            });

            document.querySelectorAll('input[name="statusExtraCharges"]').forEach(checkbox => {
                checkbox.addEventListener('change', toggleExtraChargeAmount);
            });

            // Service search input event listener
            const serviceSearchInput = document.getElementById('serviceSearch');
            if (serviceSearchInput) {
                serviceSearchInput.addEventListener('input', debounce(searchServices, 300));
                serviceSearchInput.addEventListener('blur', function () {
                    setTimeout(() => {
                        const resultsDiv = document.getElementById('serviceResults');
                        if (resultsDiv) {
                            resultsDiv.style.display = 'none';
                        }
                    }, 150);
                });
                serviceSearchInput.addEventListener('focus', function () {
                    if (this.value.length >= 2) {
                        const resultsDiv = document.getElementById('serviceResults');
                        if (resultsDiv && resultsDiv.innerHTML) {
                            resultsDiv.style.display = 'block';
                        }
                    }
                });
            }

            // Hold reason selection
            document.addEventListener('click', function (e) {
                const holdReasonOption = e.target.closest('.hold-reason');
                if (holdReasonOption) {
                    document.querySelectorAll('.hold-reason').forEach(opt => {
                        opt.classList.remove('selected');
                    });
                    holdReasonOption.classList.add('selected');

                    // Show other reason input if "other" is selected
                    const otherReasonContainer = document.getElementById('otherReasonContainer');
                    if (holdReasonOption.dataset.reason === 'other' && otherReasonContainer) {
                        otherReasonContainer.style.display = 'block';
                    } else if (otherReasonContainer) {
                        otherReasonContainer.style.display = 'none';
                    }
                    return;
                }

                // Service search results
                const serviceResult = e.target.closest('.service-result-item');
                if (serviceResult) {
                    const serviceId = parseInt(serviceResult.dataset.serviceId);
                    selectService(serviceId);
                    return;
                }

                // Customer auto-fill items
                const customerAutoItem = e.target.closest('.customer-auto-item');
                if (customerAutoItem) {
                    const customerName = customerAutoItem.dataset.customerName;
                    document.getElementById('customerName').value = customerName;
                    document.getElementById('customerAutoFill').style.display = 'none';
                    return;
                }

                // Staff selection in assignment modal
                const staffItem = e.target.closest('.staff-item');
                if (staffItem) {
                    document.querySelectorAll('.staff-item').forEach(item => {
                        item.classList.remove('selected');
                    });
                    staffItem.classList.add('selected');
                    return;
                }
            });

            // Keyboard shortcuts
            document.addEventListener('keydown', handleKeyboardShortcuts);

            // Central delegated handler for action buttons in the task table
            const table = document.getElementById('taskTable');
            if (table) {
                table.addEventListener('click', function (ev) {
                    const btn = ev.target.closest('button[data-action]');
                    if (!btn) return;
                    const action = btn.dataset.action;
                    const id = parseInt(btn.dataset.id, 10);

                    switch (action) {
                        case 'view':
                            viewTaskDetails(id);
                            break;
                        case 'edit':
                            editTask(id);
                            break;
                        case 'change-status':
                            showStatusChangeWithNotification(id);
                            break;
                        case 'assign':
                            showStaffAssignmentModal(id);
                            break;
                        case 'take':
                            showTakeTaskModal(id);
                            break;
                        case 'send-to-openplace':
                            sendTaskToOpenPlace(id);
                            break;
                        case 'hold':
                            showHoldTaskModal(id);
                            break;
                        case 'complete':
                            showCompleteTaskModal(id);
                            break;
                        case 'bill':
                            printTaskBill(id);
                            break;
                        case 'chat':
                            showCustomerChatModal(id);
                            break;
                        case 'delete':
                            deleteTask(id);
                            break;
                        case 'cancel':
                            showCancelTaskModal(id);
                            break;
                        case 'reopen':
                            // Only admin/manager should see this button; open status change modal to let them set new status
                            showStatusChangeModal(id);
                            break;
                        case 'reopen-completed':
                            // Confirm with admin before reopening completed task
                            if (confirm('Are you sure you want to reopen this completed task? This will change the status back to pending.')) {
                                reopenCompletedTask(id);
                            }
                            break;
                        default:
                            console.warn('Unhandled task action:', action);
                    }
                });
            }
        }

        function initFormEvents() {
            // Customer type change
            const customerTypeSelect = document.getElementById('customerType');
            if (customerTypeSelect) {
                customerTypeSelect.addEventListener('change', toggleOnlineForm);
            }

            // Service search
            const serviceSearch = document.getElementById('serviceSearch');
            if (serviceSearch) {
                serviceSearch.addEventListener('input', debounce(searchServices, 300));
            }

            // Customer phone lookup
            const customerPhone = document.getElementById('customerPhone');
            if (customerPhone) {
                customerPhone.addEventListener('input', debounce(checkCustomerExists, 500));
            }

            // Payment amount inputs
            const firstPaymentAmount = document.getElementById('firstPaymentAmount');
            const secondPaymentAmount = document.getElementById('secondPaymentAmount');
            if (firstPaymentAmount) {
                firstPaymentAmount.addEventListener('input', calculateTotalPaid);
            }
            if (secondPaymentAmount) {
                secondPaymentAmount.addEventListener('input', calculateTotalPaid);
            }

            // Hybrid payment inputs

            const onlineAmount = document.getElementById('onlineAmount');
            const cashAmount = document.getElementById('cashAmount');
            if (onlineAmount) {
                onlineAmount.addEventListener('input', updateHybridTotal);
            }
            if (cashAmount) {
                cashAmount.addEventListener('input', updateHybridTotal);
            }

            // Payment mode change listeners to update self-pay info
            const firstPaymentMode = document.getElementById('firstPaymentMode');
            const secondPaymentMode = document.getElementById('secondPaymentMode');
            if (firstPaymentMode) {
                firstPaymentMode.addEventListener('change', updateSelfPayFields);
            }
            if (secondPaymentMode) {
                secondPaymentMode.addEventListener('change', updateSelfPayFields);
            }

            // Customer name validation - only letters and proper case
            const customerName = document.getElementById('customerName');
            if (customerName) {
                customerName.addEventListener('input', validateCustomerName);
            }
        }

        // ========== CUSTOMER NAME VALIDATION ==========
        function validateCustomerName(event) {
            let input = event.target.value;

            // Remove any characters that are not letters and spaces
            let cleaned = input.replace(/[^a-zA-Z\s]/g, '');

            // Auto-capitalize first letter of each word but preserve the suffix spaces
            if (cleaned) {
                // Check if the input ends with a space to preserve it
                const endsWithSpace = cleaned.endsWith(' ');

                const words = cleaned.trim().split(/\s+/);
                const capitalizedWords = words.map(word => {
                    if (word.length > 0) {
                        return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
                    }
                    return word;
                });

                let result = capitalizedWords.join(' ');
                if (endsWithSpace && !result.endsWith(' ')) {
                    result += ' ';
                }
                event.target.value = result;
            } else {
                event.target.value = cleaned;
            }
        }

        // ========== KEYBOARD SHORTCUTS ==========
        function handleKeyboardShortcuts(e) {
            // Ctrl + N for new task
            if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
                e.preventDefault();
                showNewTaskModal();
                return;
            }

            // Escape to close modals
            if (e.key === 'Escape') {
                const openModals = document.querySelectorAll('.modal[style*="display: flex"]');
                if (openModals.length > 0) {
                    e.preventDefault();
                    openModals.forEach(modal => {
                        closeModal(modal.id);
                    });
                }
                return;
            }
        }

        // ========== TASK LOADING FUNCTIONS ==========
        async function loadTasks(filters = {}, tabOverride = null) {
            showLoading();
            try {
                let url = '';

                const effectiveTab = tabOverride || currentTab;

                switch (effectiveTab) {
                    case 'today':
                        url = '/api/tasks/today';
                        break;
                    case 'pending':
                        url = '/api/tasks/pending';
                        break;
                    case 'critical':
                        // Fetch pending tasks and filter client-side for >2 days old
                        url = '/api/tasks?status=pending';
                        break;
                    case 'inprogress':
                        // backend accepts status via query param
                        url = '/api/tasks?status=in_progress';
                        break;
                    case 'hold':
                        url = '/api/tasks?status=on_hold';
                        break;
                    case 'openplace':
                        url = '/api/tasks/openplace';
                        break;
                    case 'cancelled':
                        url = '/api/tasks?status=cancelled';
                        break;
                    case 'previous':
                        url = '/api/tasks/previous';
                        break;
                    case 'total':
                        url = '/api/tasks/total';
                        break;
                    case 'all':
                        const userRole = document.getElementById('currentUserRole').value;
                        if (['admin', 'manager'].includes(userRole)) {
                            url = '/api/tasks';
                        } else {
                            url = '/api/tasks/today';
                        }
                        break;
                }

                // append filters if provided
                try {
                    const qs = new URLSearchParams(filters).toString();
                    if (qs) url += (url.includes('?') ? '&' : '?') + qs;
                } catch (e) {
                    // ignore query build errors
                }

                const response = await apiFetch(url);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                tasks = await response.json();

                // If user selected the Critical Pending tab, keep only tasks
                // that have been pending for more than 2 days (48 hours)
                if (currentTab === 'critical') {
                    const cutoff = Date.now() - (2 * 24 * 60 * 60 * 1000);
                    tasks = tasks.filter(t => {
                        try {
                            const created = t.created_at ? new Date(t.created_at).getTime() : null;
                            // Only include if created_at exists and it's older than cutoff
                            return created && created <= cutoff && t.status === 'pending';
                        } catch (e) {
                            return false;
                        }
                    });
                }

                renderTaskTable();
                updateTaskStatistics(tasks);

                if (currentTab === 'openplace') {
                    updateOpenPlaceNotification(tasks.length);
                }

            } catch (error) {
                console.error('Error loading tasks:', error);
                showToast('Failed to load tasks: ' + error.message, 'error');
                tasks = [];
                renderTaskTable();
            }
            hideLoading();
        }

        async function loadOpenPlaceTasks(filter = 'all', filters = {}) {
            showLoading();
            try {
                let url = `/api/tasks/openplace?filter=${filter}`;

                // append additional filters (branch, staff, status, priority, etc.)
                try {
                    const qs = new URLSearchParams(filters).toString();
                    if (qs) url += '&' + qs;
                } catch (e) {
                    // ignore
                }

                const response = await apiFetch(url);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                tasks = await response.json();
                renderTaskTable();
                updateStatistics(tasks);
                updateOpenPlaceNotification(tasks.length);
            } catch (error) {
                console.error('Error loading open place tasks:', error);
                showToast('Failed to load open place tasks', 'error');
                tasks = [];
                renderTaskTable();
            }
            hideLoading();
        }

        // ========== OPEN PLACE FUNCTIONS ==========
        async function sendTaskToOpenPlace(taskId) {
            if (!confirm('Are you sure you want to send this task to Open Place?')) {
                return;
            }

            try {
                const response = await apiFetch(`/api/tasks/${taskId}/send-to-openplace`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        sent_by: document.getElementById('currentUsername').value,
                        sent_by_name: document.getElementById('currentUserName').value
                    })
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast('Task sent to Open Place successfully!', 'success');
                    closeModal('taskDetailsModal');
                    loadTasks();
                    checkOpenPlaceNotifications();
                } else {
                    showToast(result.error || 'Failed to send task to Open Place', 'error');
                }
            } catch (error) {
                console.error('Error sending task to Open Place:', error);
                showToast('Error sending task to Open Place', 'error');
            }
        }

        function showTakeTaskModal(taskId) {
            currentTaskId = taskId;
            const task = tasks.find(t => t.id === taskId);

            if (task) {
                const previewHtml = `
                <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 10px 0;">
                    <div><strong>Task:</strong> ${task.service_name || 'N/A'}</div>
                    <div><strong>Customer:</strong> ${task.customer_name}</div>
                    <div><strong>Priority:</strong> <span class="task-priority priority-${task.priority || 'medium'}">${formatPriority(task.priority)}</span></div>
                    ${task.department ? `<div><strong>Department:</strong> ${task.department}</div>` : ''}
                    <div><strong>Amount:</strong> ₹${task.service_price || 0}</div>
                </div>
            `;

                document.getElementById('takeTaskPreview').innerHTML = previewHtml;
                showModal('takeTaskModal');
            }
        }

        async function confirmTakeTask() {
            if (!currentTaskId) {
                showToast('No task selected', 'error');
                return;
            }

            const notes = document.getElementById('takeTaskNotes').value || '';
            const currentUser = document.getElementById('currentUsername').value;
            const currentUserName = document.getElementById('currentUserName').value;

            try {
                const response = await apiFetch(`/api/tasks/${currentTaskId}/take`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        taken_by: currentUser,
                        taken_by_name: currentUserName,
                        notes: notes
                    })
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast('Task assigned to you successfully!', 'success');
                    closeModal('takeTaskModal');
                    loadTasks();
                    checkOpenPlaceNotifications();
                } else {
                    showToast(result.error || 'Failed to take task', 'error');
                }
            } catch (error) {
                console.error('Error taking task:', error);
                showToast('Error taking task', 'error');
            }
        }

        // ========== STAFF MANAGEMENT ==========
        async function loadStaffMembers() {
            try {
                const response = await apiFetch('/api/staff');
                if (response.ok) {
                    staffMembers = await response.json();

                    // Populate specific staff select in new task modal
                    const staffSelect = document.getElementById('specificStaffSelect');
                    if (staffSelect) {
                        staffSelect.innerHTML = '<option value="">Select Staff Member</option>' +
                            staffMembers.map(staff =>
                                `<option value="${staff.username}">${staff.username} (${staff.role})</option>`
                            ).join('');
                    }

                    // Populate edit assigned to dropdown
                    const editAssignedTo = document.getElementById('editAssignedTo');
                    if (editAssignedTo) {
                        editAssignedTo.innerHTML = '<option value="">Unassigned</option>' +
                            '<option value="openplace">Open Place</option>' +
                            staffMembers.map(staff =>
                                `<option value="${staff.username}">${staff.username} (${staff.role})</option>`
                            ).join('');
                    }
                }
            } catch (error) {
                console.error('Error loading staff members:', error);
            }
        }

        async function populateStaffDropdown(dropdownId, selectedValue) {
            try {
                const response = await apiFetch('/api/staff');
                if (response.ok) {
                    const staff = await response.json();
                    const dropdown = document.getElementById(dropdownId);

                    if (dropdown) {
                        let options = '<option value="">Unassigned</option>';
                        options += '<option value="openplace">Open Place</option>';
                        options += staff.map(s =>
                            `<option value="${s.username}" ${s.username === selectedValue ? 'selected' : ''}>
                            ${s.username} (${s.role})
                        </option>`
                        ).join('');

                        dropdown.innerHTML = options;
                    }
                }
            } catch (error) {
                console.error('Error loading staff for dropdown:', error);
            }
        }

        function showStaffAssignmentModal(taskId) {
            currentTaskId = taskId;

            document.querySelectorAll('.staff-item').forEach(item => {
                item.classList.remove('selected');
            });

            const staffList = document.getElementById('staffList');
            if (staffList && staffMembers.length > 0) {
                staffList.innerHTML = staffMembers.map(staff => `
                <div class="staff-item" data-staff-id="${staff.username}" data-staff-name="${staff.username}">
                    <div style="display: flex; align-items: center;">
                        <div class="staff-avatar">${getInitials(staff.username)}</div>
                        <div class="staff-info">
                            <div class="staff-name">${staff.username}</div>
                            <div class="staff-role">${staff.role}${staff.department ? ' • ' + staff.department : ''}</div>
                        </div>
                    </div>
                    <div>
                        <small style="color: #666;">${staff.task_count || 0} tasks</small>
                    </div>
                </div>
            `).join('');
            }

            showModal('staffAssignmentModal');
        }

        async function confirmStaffAssignment() {
            if (!currentTaskId) {
                showToast('No task selected', 'error');
                return;
            }

            const selectedStaff = document.querySelector('.staff-item.selected');
            if (!selectedStaff) {
                showToast('Please select a staff member', 'error');
                return;
            }

            const staffId = selectedStaff.dataset.staffId;
            const staffName = selectedStaff.dataset.staffName;
            const notes = document.getElementById('assignmentNotes').value || '';
            const assignedBy = document.getElementById('currentUsername').value;

            const userRole = document.getElementById('currentUserRole').value;
            if (!['admin', 'manager'].includes(userRole)) {
                showToast('Only managers and admins can assign tasks to specific staff', 'error');
                return;
            }

            try {
                const response = await apiFetch(`/api/tasks/${currentTaskId}/assign`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        assigned_to: staffId,
                        assigned_to_name: staffName,
                        assigned_by: assignedBy,
                        notes: notes
                    })
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast(`Task assigned to ${staffName} successfully!`, 'success');
                    closeModal('staffAssignmentModal');
                    loadTasks();

                    const task = tasks.find(t => t.id === currentTaskId);
                    if (task && task.status === 'in_openplace') {
                        checkOpenPlaceNotifications();
                    }
                } else {
                    showToast(result.error || 'Failed to assign task', 'error');
                }
            } catch (error) {
                console.error('Error assigning task:', error);
                showToast('Error assigning task', 'error');
            }
        }

        // ========== RENDER TASK TABLE ==========
        function renderTaskTable() {
            const tableBody = document.getElementById('taskTableBody');
            const emptyState = document.getElementById('emptyState');
            const emptyStateMessage = document.getElementById('emptyStateMessage');

            if (!tableBody || !emptyState || !emptyStateMessage) {
                console.error('Table elements not found');
                return;
            }

            if (tasks.length === 0) {
                tableBody.innerHTML = '';
                emptyState.style.display = 'block';
                emptyStateMessage.textContent = `There are no ${currentTab} tasks.`;
                return;
            }

            emptyState.style.display = 'none';

            const currentUser = document.getElementById('currentUsername').value;
            const currentUserId = document.getElementById('currentUserId') ? document.getElementById('currentUserId').value : '';
            const currentUserRole = document.getElementById('currentUserRole').value;
            const currentUserDepartment = document.getElementById('currentUserDepartment').value;

            tableBody.innerHTML = tasks.map(task => {
                const isOpenPlaceTask = task.in_openplace === true || task.status === 'in_openplace' || task.assigned_to === 'open_place';

                const canTakeTask = (function () {
                    // Admins and managers can take any open place task
                    if (!isOpenPlaceTask) return false;
                    if (['admin', 'manager'].includes(currentUserRole)) return true;

                    // Staff can only take tasks for their own branch (and optionally department)
                    if (currentUserRole === 'staff') {
                        const taskBranch = task.branch || String(task.branch_id || '') || '';
                        const myBranch = document.getElementById('currentUserBranch') ? document.getElementById('currentUserBranch').value : '';
                        // require branch match
                        if (myBranch && String(taskBranch) !== String(myBranch)) return false;
                        // if task has a department, require it to match user's department
                        if (task.department && String(task.department) !== String(currentUserDepartment)) return false;
                        return true;
                    }

                    return false;
                })();

                // Admin can send any task to open place at any time
                // Manager/Staff can only send non-completed/cancelled tasks
                const canSendToOpenPlace = !isOpenPlaceTask &&
                    (currentUserRole === 'admin' ||  // Admin can always send
                        (task.status !== 'completed' &&
                            task.status !== 'cancelled' &&
                            task.status !== 'on_hold' &&
                            (task.created_by === currentUser ||
                                ['manager', 'staff'].includes(currentUserRole))));

                // Assignment to other staff should remain admin/manager only
                const canAssignToStaff = ['admin', 'manager'].includes(currentUserRole);

                const priorityClass = `priority-${task.priority || 'medium'}`;

                // Determine assignment: API may return assigned_to (id or username) or assigned_to_id / assigned_to_name
                const assignedToId = task.assigned_to || task.assigned_to_id || task.assigned_to_id_str || null;
                const assignedToName = task.assigned_to_name || task.assigned_to_username || task.assigned_to_user || null;
                const isAssignedToMe = (assignedToName && String(assignedToName) === String(currentUser)) ||
                    (assignedToId && String(assignedToId) === String(currentUserId));

                // Separate permissions: Staff can change status but CANNOT edit task details
                const canEditTask = ['admin', 'manager'].includes(currentUserRole);
                const canChangeStatus = isAssignedToMe || ['admin', 'manager', 'staff'].includes(currentUserRole);

                // Open Place specific display
                if (isOpenPlaceTask) {
                    return `
                    <tr data-task-id="${task.id}">
                        <td><strong>${task.order_no || task.id || 'N/A'}</strong></td>
                        <td>
                            <div style="font-weight: 500;">${task.customer_name}</div>
                            <small style="color: #666;">${task.customer_phone || task.contact_number || 'N/A'}</small>
                            ${task.department ? `<div class="openplace-badge"><i class="fas fa-building"></i> ${task.department}</div>` : ''}
                            ${task.sent_by_name ? `<div class="openplace-time"><i class="fas fa-share-square"></i> Sent by ${task.sent_by_name}</div>` : ''}
                        </td>
                        <td>${task.service_name || 'N/A'}</td>
                        <td>
                            <span class="status-badge openplace-status">
                                <i class="fas fa-door-open"></i> Open Place
                            </span>
                            <span class="task-priority ${priorityClass}">${formatPriority(task.priority)}</span>
                        </td>
                        <td>
                            ${task.assigned_to_name ? task.assigned_to_name : 'Available'}
                            ${task.assigned_at ? `<div class="openplace-time">${formatTimeAgo(task.assigned_at)}</div>` : ''}
                        </td>
                        <td>${formatDate(task.created_at)}</td>
                        <td>
                            <div style="font-weight: 600; color: var(--success-color);">
                                ₹${task.service_price || task.total_amount || 0}
                            </div>
                            ${task.due_amount > 0 ? `
                                <div class="due-badge" style="background: #fff3cd; color: #856404; font-size: 11px; padding: 2px 6px; border-radius: 4px; display: inline-block; margin-top: 4px; border: 1px solid #ffeaa7;">
                                    Due: ₹${task.due_amount}
                                </div>
                            ` : ''}
                        </td>
                        <td>
                            <div class="openplace-actions">
                                ${(isOpenPlaceTask && (canTakeTask || ['staff', 'admin', 'manager'].includes(currentUserRole))) ? `
                                    <button class="take-task-btn" onclick="showTakeTaskModal(${task.id})">
                                        <i class="fas fa-hand-paper"></i> Take Over
                                    </button>
                                ` : ''}
                                ${canAssignToStaff ? `
                                    <button class="action-btn action-assign" onclick="showStaffAssignmentModal(${task.id})" title="Assign to Staff">
                                        <i class="fas fa-user-tie"></i>
                                    </button>
                                ` : ''}
                                <button class="action-btn action-view" onclick="viewTaskDetails(${task.id})" title="View">
                                    <i class="fas fa-eye"></i>
                                </button>
                                <button class="action-btn action-chat" onclick="showCustomerChatModal(${task.id})" title="Customer Chat">
                                    <i class="fas fa-comments"></i>
                                </button>
                                ${task.status === 'completed' ? `
                                    <div class="bill-dropdown">
                                        <button class="action-btn action-bill" onclick="toggleBillDropdown(${task.id})" title="Bill Options"><i class="fas fa-print"></i></button>
                                        <div class="bill-dropdown-content" id="billDropdown${task.id}">
                                            <div class="bill-dropdown-item" onclick="printTaskBill(${task.id}); closeBillDropdown(${task.id});">
                                        <i class="fas fa-print"></i>
                                                <span>Print Bill</span>
                                            </div>
                                            <div class="bill-dropdown-item" onclick="shareBillWhatsApp(${task.id}); closeBillDropdown(${task.id});">
                                                <i class="fab fa-whatsapp"></i>
                                                <span>Share via WhatsApp</span>
                                            </div>
                                        </div>
                                    </div>
                                ` : ''}
                                
                                ${canUserCancelTask() && task.status !== 'completed' && task.status !== 'cancelled' ? `
                                    <button class="action-btn action-cancel" onclick="showCancelTaskModal(${task.id})" title="Cancel Task">
                                        <i class="fas fa-times-circle"></i>
                                    </button>
                                ` : ''}
                            </div>
                        </td>
                    </tr>
                `;
                }

                // Regular task display
                const isBusiness = (task.service_type || 'normal') === 'business';

                return `
                <tr data-task-id="${task.id}" class="${isBusiness ? 'task-business' : ''}">
                    <td><strong>${task.order_no || task.id || 'N/A'}</strong></td>
                    <td>
                        <div style="font-weight: 500;">${task.customer_name}</div>
                        <small style="color: #666;">${task.customer_phone || task.contact_number || 'N/A'}</small>
                        <div style="display: flex; gap: 5px; flex-wrap: wrap;">
                            ${task.department ? `<div class="openplace-badge"><i class="fas fa-building"></i> ${task.department}</div>` : ''}
                            ${isBusiness ? `<div class="business-badge"><i class="fas fa-briefcase"></i> Business</div>` : ''}
                        </div>
                    </td>
                    <td>${task.service_name || 'N/A'}</td>
                    <td>
                        <span class="status-badge status-${task.status}">
                            ${formatStatus(task.status)}
                        </span>
                        <span class="task-priority ${priorityClass}">${formatPriority(task.priority)}</span>
                    </td>
                    <td>${task.assigned_to_name || 'Unassigned'}</td>
                    <td>${formatDate(task.created_at)}</td>
                    <td>
                        <div style="font-weight: 600; color: var(--success-color);">
                            ₹${task.service_price || task.total_amount || 0}
                        </div>
                        ${task.due_amount > 0 ? `
                            <div class="due-badge" style="background: #fff3cd; color: #856404; font-size: 11px; padding: 2px 6px; border-radius: 4px; display: inline-block; margin-top: 4px; border: 1px solid #ffeaa7;">
                                Due: ₹${task.due_amount}
                            </div>
                        ` : ''}
                    </td>
                    <td>
                        <div class="action-buttons-cell">
                            ${(() => {
                        let buttons = '';
                        // Always allow view and chat
                        buttons += `<button class="action-btn action-view" data-action="view" data-id="${task.id}" title="View"><i class="fas fa-eye"></i></button>`;
                        buttons += `<button class="action-btn action-chat" data-action="chat" data-id="${task.id}" title="Customer Chat"><i class="fas fa-comments"></i></button>`;

                        // If task is cancelled: restrict actions. Only admin/manager can reopen or delete.
                        if (task.status === 'cancelled') {
                            if (['admin', 'manager'].includes(currentUserRole)) {
                                buttons += `<button class="action-btn action-reopen" data-action="reopen" data-id="${task.id}" title="Reopen Task"><i class="fas fa-redo"></i></button>`;
                            }
                            if (canUserDeleteTask() && (task.created_by === currentUser || currentUserRole === 'admin')) {
                                buttons += `<button class="action-btn action-delete" data-action="delete" data-id="${task.id}" title="Delete"><i class="fas fa-trash"></i></button>`;
                            }
                            return buttons;
                        }

                        // Normal actions for non-cancelled tasks
                        if (task.status !== 'completed') {
                            // Allow editing only for Admin/Manager AND when not on hold
                            if (canEditTask && task.status !== 'on_hold') {
                                buttons += `<button class="action-btn action-edit" data-action="edit" data-id="${task.id}" title="Edit Task"><i class="fas fa-edit"></i></button>`;
                            }

                            // Allow changing status for Staff/Admin/Manager even when task is on hold
                            if (canChangeStatus) {
                                buttons += `<button class="action-btn action-edit" data-action="change-status" data-id="${task.id}" title="Change Status"><i class="fas fa-exchange-alt"></i></button>`;
                            }
                        }

                        if (canAssignToStaff) {
                            buttons += `<button class="action-btn action-assign" data-action="assign" data-id="${task.id}" title="Assign to Staff"><i class="fas fa-user-tie"></i></button>`;
                        }

                        if (canSendToOpenPlace) {
                            buttons += `<button class="action-btn action-openplace" data-action="send-to-openplace" data-id="${task.id}" title="Send to Open Place"><i class="fas fa-door-open"></i></button>`;
                        }

                        if (canChangeStatus && task.status !== 'completed') {
                            buttons += `<button class="action-btn action-complete" data-action="complete" data-id="${task.id}" title="Complete"><i class="fas fa-check"></i></button>`;
                            buttons += `<button class="action-btn action-hold" data-action="hold" data-id="${task.id}" title="Hold"><i class="fas fa-pause"></i></button>`;
                        }

                        if (task.status === 'completed') {
                            buttons += `<button class="action-btn action-bill" data-action="bill" data-id="${task.id}" title="Print Bill"><i class="fas fa-print"></i></button>`;

                            // Admin-only button to reopen completed task
                            if (currentUserRole === 'admin') {
                                buttons += `<button class="action-btn action-reopen-completed" data-action="reopen-completed" data-id="${task.id}" title="Reopen Completed Task (Admin Only)"><i class="fas fa-redo"></i></button>`;
                            }
                        }

                        // Show delete button only for admins
                        if (canUserDeleteTask() && (task.created_by === currentUser || currentUserRole === 'admin')) {
                            buttons += `<button class="action-btn action-delete" data-action="delete" data-id="${task.id}" title="Delete"><i class="fas fa-trash"></i></button>`;
                        }

                        // Show cancel button for authorized users if task is not completed or cancelled
                        if (canUserCancelTask() && task.status !== 'completed' && task.status !== 'cancelled') {
                            buttons += `<button class="action-btn action-cancel" data-action="cancel" data-id="${task.id}" title="Cancel Task"><i class="fas fa-times-circle"></i></button>`;
                        }

                        return buttons;
                    })()}
                        </div>
                    </td>
                </tr>
            `;
            }).join('');
        }

        // ========== NEW TASK MODAL FUNCTIONS ==========
        function showNewTaskModal() {
            resetNewTaskForm();
            showModal('newTaskModal');
        }

        function resetNewTaskForm() {
            const form = document.getElementById('newTaskForm');
            if (form) {
                form.reset();
                selectedService = null;
                document.getElementById('selectedServiceInfo').classList.add('hidden');
                selectAssignment('myself');
                document.getElementById('onlineCustomerForm').style.display = 'none';
                document.getElementById('selfPayInfo').style.display = 'none';
                document.getElementById('hybridPaymentSection').style.display = 'none';
            }
        }

        async function loadBranches() {
            try {
                const response = await apiFetch('/api/branches/all');
                if (response.ok) {
                    const branches = await response.json();
                    const branchSelect = document.getElementById('branchSelect');
                    if (branchSelect) {
                        branchSelect.innerHTML = '<option value="">Select Branch</option>' +
                            branches.map(branch =>
                                `<option value="${branch.id}">${branch.name}</option>`
                            ).join('');
                    }
                }
            } catch (error) {
                console.error('Error loading branches:', error);
            }
        }

        function selectAssignment(type) {
            document.querySelectorAll('.assignment-option').forEach(opt => {
                opt.classList.remove('selected');
            });

            if (type === 'myself') {
                document.getElementById('assignMyself').classList.add('selected');
                document.getElementById('selectedAssignment').value = 'myself';
                document.getElementById('specificStaffSection').style.display = 'none';
            } else if (type === 'openplace') {
                document.getElementById('assignOpenPlace').classList.add('selected');
                document.getElementById('selectedAssignment').value = 'openplace';
                document.getElementById('specificStaffSection').style.display = 'none';
            } else if (type === 'specific') {
                document.getElementById('assignSpecific').classList.add('selected');
                document.getElementById('selectedAssignment').value = 'specific';
                document.getElementById('specificStaffSection').style.display = 'block';

                const userRole = document.getElementById('currentUserRole').value;
                if (!['admin', 'manager'].includes(userRole)) {
                    showToast('Only managers and admins can assign tasks to specific staff', 'warning');
                    selectAssignment('myself');
                }
            }
        }

        async function submitTask() {
            try {
                const form = document.getElementById('newTaskForm');
                if (!form.checkValidity()) {
                    form.reportValidity();
                    return;
                }

                const formData = {
                    customer_name: document.getElementById('customerName').value,
                    customer_phone: document.getElementById('customerPhone').value,
                    service_type: document.getElementById('serviceType').value,
                    priority: document.getElementById('taskPriority').value,
                    description: document.getElementById('taskDescription').value,
                    assignment_type: document.getElementById('selectedAssignment').value
                };

                if (selectedService) {
                    formData.service_id = selectedService.id;
                    // Use service.price (total customer pays), not service.charge (company profit)
                    formData.service_price = selectedService.price;
                }

                const firstPaymentAmount = parseFloat(document.getElementById('firstPaymentAmount').value) || 0;
                const secondPaymentAmount = parseFloat(document.getElementById('secondPaymentAmount').value) || 0;
                formData.paid_amount = firstPaymentAmount + secondPaymentAmount;

                const assignmentType = document.getElementById('selectedAssignment').value;
                if (assignmentType === 'specific') {
                    const staffUsername = document.getElementById('specificStaffSelect').value;
                    if (staffUsername) {
                        const staff = staffMembers.find(s => s.username === staffUsername);
                        if (staff) {
                            formData.assigned_to = staff.username;
                        }
                    }
                }

                const customerType = document.getElementById('customerType').value;
                const paymentModeEl = document.getElementById('paymentMode') || document.getElementById('firstPaymentMode');
                const paymentMode = paymentModeEl ? paymentModeEl.value : (customerType === 'online' ? 'online' : 'cash');

                if (customerType === 'online') {
                    const branchId = document.getElementById('branchSelect').value;

                    if (!branchId || (paymentModeEl && !paymentMode)) {
                        showToast('Please select branch and payment mode for online customer', 'error');
                        return;
                    }

                    formData.customer_type = 'online';
                    formData.branch_id = branchId;
                    formData.payment_mode = paymentMode;

                    const branchSelect = document.getElementById('branchSelect');
                    const selectedOption = branchSelect.options[branchSelect.selectedIndex];
                    formData.branch_name = selectedOption.text;

                    if (paymentMode === 'hybrid') {
                        const onlineAmount = parseFloat(document.getElementById('onlineAmount').value) || 0;
                        const cashAmount = parseFloat(document.getElementById('cashAmount').value) || 0;
                        formData.online_payment = onlineAmount;
                        formData.cash_payment = cashAmount;
                    }
                } else {
                    formData.payment_mode = paymentMode;
                }

                // Strict validation for Self-Pay
                const firstPaymentModeVal = document.getElementById('firstPaymentMode').value;
                const firstPaymentAmountVal = parseFloat(document.getElementById('firstPaymentAmount').value) || 0;

                if (firstPaymentModeVal === 'self_pay' && selectedService) {
                    const requiredFee = selectedService.fee || 0;
                    if (Math.abs(firstPaymentAmountVal - requiredFee) > 0.01) {
                        showToast(`Self-Pay amount (₹${firstPaymentAmountVal}) must match Govt Fee (₹${requiredFee}) exactly.`, 'error');
                        return;
                    }
                }

                console.log('Submitting task:', formData);

                const response = await apiFetch('/api/tasks', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast('Task created successfully!', 'success');
                    closeModal('newTaskModal');
                    loadTasks();

                    if (formData.assignment_type === 'openplace') {
                        checkOpenPlaceNotifications();
                    }
                } else {
                    showToast(result.error || 'Failed to create task', 'error');
                }

            } catch (error) {
                console.error('Error submitting task:', error);
                showToast('Error creating task: ' + error.message, 'error');
            }
        }

        // ========== EDIT TASK FUNCTIONS ==========
        async function editTask(taskId) {
            currentTaskId = taskId;

            try {
                // Fetch task details
                const response = await apiFetch(`/api/tasks/${taskId}`);
                if (!response.ok) throw new Error('Failed to load task details');

                const task = await response.json();

                // Populate the edit form
                document.getElementById('editTaskId').value = task.id;
                document.getElementById('editCustomerName').value = task.customer_name || '';
                document.getElementById('editCustomerPhone').value = task.customer_phone || task.contact_number || '';
                document.getElementById('editServiceName').value = task.service_name || 'N/A';
                document.getElementById('editServicePrice').value = task.service_price || 0;
                document.getElementById('editPaidAmount').value = task.paid_amount || 0;
                document.getElementById('editPaymentMode').value = task.payment_mode || '';
                document.getElementById('editPriority').value = task.priority || 'medium';
                document.getElementById('editStatus').value = task.status || 'pending';
                document.getElementById('editDescription').value = task.description || '';

                // Populate staff dropdown
                await populateStaffDropdown('editAssignedTo', task.assigned_to || '');

                showModal('editTaskModal');
            } catch (error) {
                console.error('Error loading task for editing:', error);
                showToast('Failed to load task details for editing', 'error');
            }
        }

        function resetEditTaskForm() {
            const form = document.getElementById('editTaskForm');
            if (form) {
                form.reset();
                document.getElementById('editTaskId').value = '';
            }
        }

        async function updateTask() {
            if (!currentTaskId) {
                showToast('No task selected', 'error');
                return;
            }

            try {
                const formData = {
                    customer_name: document.getElementById('editCustomerName').value,
                    customer_phone: document.getElementById('editCustomerPhone').value,
                    paid_amount: parseFloat(document.getElementById('editPaidAmount').value) || 0,
                    payment_mode: document.getElementById('editPaymentMode').value,
                    priority: document.getElementById('editPriority').value,
                    status: document.getElementById('editStatus').value,
                    description: document.getElementById('editDescription').value,
                    assigned_to: document.getElementById('editAssignedTo').value
                };

                // Validate required fields
                if (!formData.customer_name || !formData.customer_phone) {
                    showToast('Customer name and phone are required', 'error');
                    return;
                }

                // Validate phone number
                if (!/^\d{10}$/.test(formData.customer_phone)) {
                    showToast('Please enter a valid 10-digit phone number', 'error');
                    return;
                }

                const response = await apiFetch(`/api/tasks/${currentTaskId}/update`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast('Task updated successfully!', 'success');
                    closeModal('editTaskModal');
                    loadTasks(); // Refresh the task list
                } else {
                    showToast(result.error || 'Failed to update task', 'error');
                }
            } catch (error) {
                console.error('Error updating task:', error);
                showToast('Error updating task: ' + error.message, 'error');
            }
        }

        // ========== TASK DETAILS MODAL ==========
        async function viewTaskDetails(taskId) {
            try {
                const response = await apiFetch(`/api/tasks/${taskId}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const task = await response.json();
                const statusHistory = task.status_history || [];

                currentTaskId = taskId;

                const currentUserRole = document.getElementById('currentUserRole').value;
                const currentUser = document.getElementById('currentUsername').value;

                // Admin can send any task to openplace at any time
                // Others can only send non-completed/cancelled tasks they created
                const canSendToOpenPlace = task.status !== 'in_openplace' &&
                    (currentUserRole === 'admin' ||  // Admin can always send
                        (task.status !== 'completed' &&
                            task.status !== 'cancelled' &&
                            (task.created_by === currentUser ||
                                ['manager'].includes(currentUserRole))));

                const sendToOpenPlaceBtn = document.getElementById('sendToOpenPlaceBtn');
                if (sendToOpenPlaceBtn) {
                    sendToOpenPlaceBtn.style.display = canSendToOpenPlace ? 'inline-flex' : 'none';
                }

                // Handle admin-only buttons
                const editTaskBtn = document.getElementById('editTaskBtn');
                const reopenTaskBtn = document.getElementById('reopenTaskBtn');

                if (currentUserRole === 'admin') {
                    if (task.status === 'completed') {
                        // Show Reopen button and hide Edit button for completed tasks
                        if (reopenTaskBtn) reopenTaskBtn.style.display = 'inline-flex';
                        if (editTaskBtn) editTaskBtn.style.display = 'none';

                        // Add event listener for reopen button
                        if (reopenTaskBtn) {
                            reopenTaskBtn.onclick = function () {
                                if (confirm('Are you sure you want to reopen this completed task? This will change the status back to pending.')) {
                                    reopenCompletedTask(taskId);
                                }
                            };
                        }
                    } else {
                        // Show Edit button and hide Reopen button for non-completed tasks
                        if (editTaskBtn) editTaskBtn.style.display = 'inline-flex';
                        if (reopenTaskBtn) reopenTaskBtn.style.display = 'none';

                        // Add event listener for edit button
                        if (editTaskBtn) {
                            editTaskBtn.onclick = function () {
                                closeModal('taskDetailsModal');
                                editTask(taskId);
                            };
                        }
                    }
                } else if (currentUserRole === 'manager') {
                    // Managers see Edit button for non-completed tasks
                    if (editTaskBtn) {
                        editTaskBtn.style.display = task.status !== 'completed' ? 'inline-flex' : 'none';
                        editTaskBtn.onclick = function () {
                            closeModal('taskDetailsModal');
                            editTask(taskId);
                        };
                    }
                    if (reopenTaskBtn) reopenTaskBtn.style.display = 'none';
                } else {
                    // Regular staff don't see either button
                    if (editTaskBtn) editTaskBtn.style.display = 'none';
                    if (reopenTaskBtn) reopenTaskBtn.style.display = 'none';
                }

                const detailsContent = document.getElementById('taskDetailsContent');
                if (detailsContent) {
                    let paymentInfo = '';
                    if (task.payment_mode) {
                        paymentInfo = `
                        <div class="detail-row">
                            <span class="detail-label">Payment Mode:</span>
                            <span class="detail-value">${formatPaymentMode(task.payment_mode)}</span>
                        </div>
                    `;
                        if (task.hybrid_payment) {
                            paymentInfo += `
                            <div class="detail-row">
                                <span class="detail-label">Online Payment:</span>
                                <span class="detail-value">₹${task.online_payment || 0}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Cash Payment:</span>
                                <span class="detail-value">₹${task.cash_payment || 0}</span>
                            </div>
                        `;
                        }
                    }

                    detailsContent.innerHTML = `
                    <div class="task-detail-section">
                        <h4>Task Information</h4>
                        <div class="detail-row">
                            <span class="detail-label">Order No:</span>
                            <span class="detail-value">${task.order_no || 'N/A'}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Customer:</span>
                            <span class="detail-value">${task.customer_name} (${task.customer_phone || task.contact_number || 'N/A'})</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Service:</span>
                            <span class="detail-value">${task.service_name || 'N/A'}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Amount:</span>
                            <span class="detail-value">₹${task.service_price || 0}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Paid Amount:</span>
                            <span class="detail-value">₹${task.paid_amount || 0}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Due Amount:</span>
                            <span class="detail-value">₹${task.due_amount !== undefined ? task.due_amount : Math.max(0, (task.total_amount || task.service_price || 0) - (task.paid_amount || 0))}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Status:</span>
                            <span class="detail-value status-badge status-${task.status}">${formatStatus(task.status)}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Priority:</span>
                            <span class="detail-value">${formatPriority(task.priority)}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Assigned To:</span>
                            <span class="detail-value">${task.assigned_to_name || 'Unassigned'}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Created By:</span>
                            <span class="detail-value">${task.created_by || 'N/A'}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Created At:</span>
                            <span class="detail-value">${formatDate(task.created_at)}</span>
                        </div>
                        ${paymentInfo}
                        ${task.description ? `
                            <div class="detail-row">
                                <span class="detail-label">Description:</span>
                                <span class="detail-value">${task.description}</span>
                            </div>
                        ` : ''}
                        ${task.department ? `
                            <div class="detail-row">
                                <span class="detail-label">Department:</span>
                                <span class="detail-value">${task.department}</span>
                            </div>
                        ` : ''}
                    </div>
                `;
                }

                const statusHistoryDiv = document.getElementById('statusHistory');
                if (statusHistoryDiv) {
                    if (statusHistory && statusHistory.length > 0) {
                        statusHistoryDiv.innerHTML = `
                        <h4>Status History</h4>
                        <div class="status-timeline">
                            ${statusHistory.map(history => `
                                <div class="timeline-item">
                                    <div class="timeline-marker"></div>
                                    <div class="timeline-content">
                                        <div class="timeline-header">
                                            <span class="status-change">${formatStatus(history.old_status)} → ${formatStatus(history.new_status)}</span>
                                            <span class="timeline-time">${formatDate(history.changed_at)}</span>
                                        </div>
                                        ${history.reason ? `<div class="timeline-reason">${history.reason}</div>` : ''}
                                        <div class="timeline-by">Changed by: ${history.changed_by}</div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                    } else {
                        statusHistoryDiv.innerHTML = '<p>No status history available.</p>';
                    }
                }

                showModal('taskDetailsModal');
            } catch (error) {
                console.error('Error loading task details:', error);
                showToast('Failed to load task details', 'error');
            }
        }

        // ========== OPEN PLACE NOTIFICATION ==========
        async function checkOpenPlaceNotifications() {
            try {
                const response = await apiFetch('/api/tasks/openplace/count');
                if (response.ok) {
                    const data = await response.json();
                    openplaceNotifications = data.count || 0;

                    const notificationCount = document.getElementById('openplaceNotificationCount');
                    if (notificationCount) {
                        if (openplaceNotifications > 0) {
                            notificationCount.textContent = openplaceNotifications;
                            notificationCount.style.display = 'inline-flex';
                        } else {
                            notificationCount.style.display = 'none';
                        }
                    }

                    const navCount = document.getElementById('openplaceNavCount');
                    if (navCount) {
                        if (openplaceNotifications > 0) {
                            navCount.textContent = openplaceNotifications;
                            navCount.style.display = 'inline-flex';
                        } else {
                            navCount.style.display = 'none';
                        }
                    }
                }
            } catch (error) {
                console.error('Error checking open place notifications:', error);
            }
        }

        function updateOpenPlaceNotification(count) {
            openplaceNotifications = count;

            const notificationCount = document.getElementById('openplaceNotificationCount');
            if (notificationCount) {
                if (openplaceNotifications > 0) {
                    notificationCount.textContent = openplaceNotifications;
                    notificationCount.style.display = 'inline-flex';
                } else {
                    notificationCount.style.display = 'none';
                }
            }

            const navCount = document.getElementById('openplaceNavCount');
            if (navCount) {
                if (openplaceNotifications > 0) {
                    navCount.textContent = openplaceNotifications;
                    navCount.style.display = 'inline-flex';
                } else {
                    navCount.style.display = 'none';
                }
            }
        }

        // ========== STATISTICS ==========
        async function loadStatistics() {
            try {
                const response = await apiFetch('/api/stats');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const stats = await response.json();
                updateStatisticsDisplay(stats);
            } catch (error) {
                console.error('Error loading statistics:', error);
            }
        }

        function updateTaskStatistics(tasks) {
            // Alias for backwards compatibility with older callers
            updateStatistics(tasks);
        }

        function updateStatistics(tasks) {
            const stats = {
                total: tasks.length,
                pending: tasks.filter(t => t.status === 'pending').length,
                in_progress: tasks.filter(t => t.status === 'in_progress').length,
                openplace: tasks.filter(t => t.status === 'in_openplace' || t.assigned_to === 'open_place').length,
                completed: tasks.filter(t => t.status === 'completed').length,
                on_hold: tasks.filter(t => t.status === 'on_hold').length
            };
            updateStatisticsDisplay(stats);
        }

        function updateStatisticsDisplay(stats) {
            const elements = {
                'totalTasks': 'total',
                'pendingTasks': 'pending',
                'inProgressTasks': 'in_progress',
                'openplaceTasks': 'openplace',
                'completedTasks': 'completed',
                'onHoldTasks': 'on_hold'
            };

            for (const [elementId, statKey] of Object.entries(elements)) {
                const element = document.getElementById(elementId);
                if (element) {
                    element.textContent = stats[statKey] || 0;
                }
            }
        }

        // ========== FORM HELPER FUNCTIONS ==========
        function toggleOnlineForm() {
            const customerType = document.getElementById('customerType').value;
            const onlineForm = document.getElementById('onlineCustomerForm');

            if (customerType === 'online') {
                onlineForm.style.display = 'block';
            } else {
                onlineForm.style.display = 'none';
            }
        }

        function calculateTotalPaid() {
            const firstPayment = parseFloat(document.getElementById('firstPaymentAmount').value) || 0;
            const secondPayment = parseFloat(document.getElementById('secondPaymentAmount').value) || 0;
            const totalPaid = firstPayment + secondPayment;

            document.getElementById('totalPaidAmount').value = totalPaid;

            if (selectedService) {
                const isBusiness = (selectedService.service_type === 'business');

                // Determine target total based on self-pay mode
                const firstMode = document.getElementById('firstPaymentMode').value;
                const secondMode = document.getElementById('secondPaymentMode').value;
                const isSelfPay = firstMode === 'self_pay' || secondMode === 'self_pay';

                // Target Total Logic:
                // If NOT Self-Pay: NORMAL uses price, BUSINESS uses charge.
                // If Self-Pay: We only collect the FEE. (Note: back-end might handle split, but UI shows what company collects)
                const targetTotal = isSelfPay ? (selectedService.fee || 0) : (isBusiness ? (selectedService.charge || 0) : (selectedService.price || 0));

                const dueAmount = targetTotal - totalPaid;
                document.getElementById('dueAmountInput').value = dueAmount > 0 ? dueAmount.toFixed(2) : 0;

                // Show extra payment notice if user pays more than the target collection
                const extraNotice = document.getElementById('extraPaymentNotice');
                const extraAmtDisplay = document.getElementById('extraAmountDisplay');

                const extraAmount = totalPaid - targetTotal;

                if (isSelfPay && extraAmount > 0) {
                    if (extraAmtDisplay) {
                        extraAmtDisplay.textContent = extraAmount.toFixed(2);
                    }
                    extraNotice.style.display = 'block';
                } else {
                    extraNotice.style.display = 'none';
                }
            }
        }

        async function searchServices() {
            const query = document.getElementById('serviceSearch').value;
            if (query.length < 2) {
                document.getElementById('serviceResults').innerHTML = '';
                document.getElementById('serviceResults').style.display = 'none';
                return;
            }

            try {
                const response = await apiFetch(`/api/services/search?q=${encodeURIComponent(query)}`);
                if (response.ok) {
                    const services = await response.json();
                    const resultsDiv = document.getElementById('serviceResults');

                    if (services.length > 0) {
                        resultsDiv.innerHTML = services.map(service => {
                            // Show service.price (total) for customers, not service.charge (profit)
                            const displayPrice = service.price || 0;
                            return `
                        <div class="service-result-item" data-service-id="${service.id}" style="cursor: pointer; padding: 10px; border-bottom: 1px solid #eee;">
                            <div class="service-result-name" style="font-weight: 600;">${service.name}</div>
                            <div class="service-result-price" style="color: #4CAF50; font-weight: bold;">₹${displayPrice}</div>
                            <div class="service-result-type" style="font-size: 12px; color: #999;">${service.service_type}</div>
                        </div>
                    `;
                        }).join('');
                        resultsDiv.style.display = 'block';

                        // Add click handlers to result items
                        document.querySelectorAll('.service-result-item').forEach(item => {
                            item.addEventListener('click', function () {
                                const serviceId = this.getAttribute('data-service-id');
                                selectService(serviceId);
                            });
                        });
                    } else {
                        resultsDiv.innerHTML = '<div class="no-results" style="padding: 10px; text-align: center; color: #999;">No services found</div>';
                        resultsDiv.style.display = 'block';
                    }
                }
            } catch (error) {
                console.error('Error searching services:', error);
                showToast('Error searching services', 'error');
            }
        }

        async function selectService(serviceId) {
            try {
                const response = await apiFetch(`/api/services/${serviceId}`);
                if (response.ok) {
                    selectedService = await response.json();

                    const isBusiness = (selectedService.service_type === 'business');

                    // Close dropdown and update search input
                    document.getElementById('serviceSearch').value = selectedService.name;
                    document.getElementById('serviceResults').innerHTML = '';
                    document.getElementById('serviceResults').style.display = 'none';

                    // Show service details
                    document.getElementById('selectedServiceInfo').classList.remove('hidden');

                    // Business logic: price = charge + fee (total customer pays)
                    // charge = service charge (company profit/revenue)
                    // fee = government fee
                    const totalVisible = isBusiness ? (selectedService.charge || 0) : (selectedService.price || 0);

                    document.getElementById('servicePriceDisplay').textContent = `₹${totalVisible}`;

                    document.getElementById('basePrice').textContent = `₹${selectedService.price || 0}`;
                    document.getElementById('serviceFee').textContent = `₹${selectedService.fee || 0}`;
                    document.getElementById('serviceCharge').textContent = `₹${selectedService.charge || 0}`;
                    document.getElementById('totalPrice').textContent = `₹${totalVisible}`;

                    updateSelfPayFields();
                    showToast(`${selectedService.name} selected successfully`, 'success');
                }
            } catch (error) {
                console.error('Error selecting service:', error);
                showToast('Failed to load service details', 'error');
            }
        }

        async function checkCustomerExists() {
            const phone = document.getElementById('customerPhone').value;
            if (phone.length >= 10) {
                try {
                    const response = await apiFetch(`/api/customers/check?phone=${phone}`);
                    if (response.ok) {
                        const data = await response.json();
                        const autoFill = document.getElementById('customerAutoFill');

                        if (data.exists) {
                            autoFill.innerHTML = `
                            <div class="customer-auto-item" data-customer-name="${data.name}">
                                <i class="fas fa-user"></i>
                                ${data.name} - ${phone}
                                <small>(${data.total_services} services, ₹${data.total_spent} spent)</small>
                            </div>
                        `;
                            autoFill.style.display = 'block';
                        } else {
                            autoFill.style.display = 'none';
                        }
                    }
                } catch (error) {
                    console.error('Error checking customer:', error);
                }
            } else {
                document.getElementById('customerAutoFill').style.display = 'none';
            }
        }

        function updateSelfPayFields() {
            const firstModeEl = document.getElementById('firstPaymentMode');
            const secondModeEl = document.getElementById('secondPaymentMode');
            const firstAmountEl = document.getElementById('firstPaymentAmount');

            const firstMode = firstModeEl.value;
            const secondMode = secondModeEl.value;
            const isSelfPay = firstMode === 'self_pay' || secondMode === 'self_pay';

            const isBusiness = selectedService ? (selectedService.service_type === 'business') : false;
            // Business logic: price = charge + fee (total), charge = company profit, fee = govt fee
            const servicePrice = selectedService ? (isBusiness ? (selectedService.charge || 0) : (selectedService.price || 0)) : 0;
            const serviceFee = selectedService ? (selectedService.fee || 0) : 0;
            const basePrice = selectedService ? (selectedService.price || 0) : 0; // The actual price field (total)

            // Mutex Logic: Hide "Self-Pay" in one if selected in other
            const selfPayOptionValue = 'self_pay';

            // Handle Second Dropdown visibility based on First
            for (let i = 0; i < secondModeEl.options.length; i++) {
                if (secondModeEl.options[i].value === selfPayOptionValue) {
                    if (firstMode === selfPayOptionValue) {
                        secondModeEl.options[i].style.display = 'none';
                        if (secondMode === selfPayOptionValue) secondModeEl.value = ''; // Reset if hidden
                    } else {
                        secondModeEl.options[i].style.display = 'block';
                    }
                }
            }

            // Handle First Dropdown visibility based on Second
            for (let i = 0; i < firstModeEl.options.length; i++) {
                if (firstModeEl.options[i].value === selfPayOptionValue) {
                    if (secondMode === selfPayOptionValue) {
                        firstModeEl.options[i].style.display = 'none';
                        // Don't reset first value here as it drives the logic usually, just hide option for future
                    } else {
                        firstModeEl.options[i].style.display = 'block';
                    }
                }
            }

            if (isSelfPay) {
                // HIDE Self-Pay if service price is less than fee (invalid state)


                // Auto-fill company collection (service_fee = govt fee) and lock it
                if (firstMode === 'self_pay') {
                    if (!firstAmountEl.value || firstAmountEl.readOnly) {
                        firstAmountEl.value = serviceFee;
                    }
                    firstAmountEl.readOnly = true;
                } else if (secondMode === 'self_pay') {
                    firstAmountEl.readOnly = false;
                }

                // In self-pay mode, customer pays Provider (the actual price/total), 
                // but company only collects service_fee (govt fee).
                const customerPays = basePrice;

                document.getElementById('selfPayInfo').style.display = 'block';
                document.getElementById('selfPayServicePrice').textContent = `₹${servicePrice}`;
                document.getElementById('selfPayServiceFee').textContent = `₹${serviceFee}`;
                document.getElementById('selfPayCustomerPays').textContent = `₹${customerPays}`;
                document.getElementById('selfPayRevenue').textContent = `₹${serviceFee}`;

                document.getElementById('isSelfPay').value = 'true';
            } else {
                firstAmountEl.readOnly = false;
                document.getElementById('selfPayInfo').style.display = 'none';
                document.getElementById('isSelfPay').value = 'false';
            }

            // Logic to hide 'self_pay' option if service price (total) < fee (invalid state)
            if (servicePrice < serviceFee) {
                for (let i = 0; i < firstModeEl.options.length; i++) {
                    if (firstModeEl.options[i].value === 'self_pay') {
                        firstModeEl.options[i].style.display = 'none';
                    }
                }
                if (secondModeEl) {
                    for (let i = 0; i < secondModeEl.options.length; i++) {
                        if (secondModeEl.options[i].value === 'self_pay') {
                            secondModeEl.options[i].style.display = 'none';
                        }
                    }
                }
            }

            // Recalculate totals based on possibly new target total
            calculateTotalPaid();

            if (firstMode === 'hybrid' || (secondModeEl && secondModeEl.value === 'hybrid')) {
                document.getElementById('hybridPaymentSection').style.display = 'block';
            } else {
                document.getElementById('hybridPaymentSection').style.display = 'none';
            }
        }

        function updateHybridTotal() {
            const onlineAmount = parseFloat(document.getElementById('onlineAmount').value) || 0;
            const cashAmount = parseFloat(document.getElementById('cashAmount').value) || 0;
            const total = onlineAmount + cashAmount;

            const validationMessage = document.getElementById('hybridValidationMessage');
            if (selectedService && total > selectedService.charge) {
                validationMessage.textContent = 'Total hybrid payment exceeds service charge (profit)!';
                validationMessage.style.display = 'block';
                validationMessage.style.color = 'red';
            } else {
                validationMessage.style.display = 'none';
            }
        }

        function handleDuePaymentModeChange() {
            const paymentMode = document.getElementById('duePaymentMode').value;
            const hybridSection = document.getElementById('hybridBreakdownSection');
            const selfPaySection = document.getElementById('selfPayConfirmation');

            updateExtraLabel(paymentMode, 'extraChargesLabel');

            hybridSection.style.display = 'none';
            // Show selfPaySection if mode is self_pay OR if self-pay flag is active
            selfPaySection.style.display = (paymentMode === 'self_pay' || isSelfPayCompletionActive) ? 'block' : 'none';

            if (paymentMode === 'hybrid') {
                hybridSection.style.display = 'flex';
            }

            // Sync dynamic govt fee header if visible
            if (selfPaySection.style.display === 'block') {
                const task = tasks.find(t => t.id === currentTaskId);
                if (task) {
                    const fee = parseFloat(task.service_fee) || 0;
                    const header = document.getElementById('selfPayFeeHeader');
                    if (header) header.textContent = `Govt Fees Amount: ₹${fee.toFixed(2)}`;
                }
            }
        }

        function handleStatusPaymentModeChange() {
            const paymentMode = document.getElementById('statusPaymentMode').value;
            updateExtraLabel(paymentMode, 'statusExtraChargesLabel');
        }

        function updateExtraLabel(mode, labelId) {
            const label = document.getElementById(labelId);
            if (!label) return;

            if (mode === 'self_pay') {
                label.innerHTML = '<i class="fas fa-plus-circle"></i> Govt Fees (extra collected)';
            } else {
                label.innerHTML = '<i class="fas fa-plus-circle"></i> Extra Amount (if any)';
            }
        }

        function validateHybridPayment() {
            const onlineAmount = parseFloat(document.getElementById('hybridOnlineAmount').value) || 0;
            const cashAmount = parseFloat(document.getElementById('hybridCashAmount').value) || 0;
            const dueAmount = parseFloat(document.getElementById('dueAmount').value) || 0;
            const total = onlineAmount + cashAmount;

            if (Math.abs(total - dueAmount) > 0.01) {
                showToast('Hybrid payment total must equal due amount', 'error');
                return false;
            }
            return true;
        }

        function toggleExtraChargeAmount(event) {
            const checkbox = event.target;
            const amountField = checkbox.nextElementSibling.nextElementSibling;
            if (checkbox.checked) {
                amountField.disabled = false;
                amountField.focus();
            } else {
                amountField.disabled = true;
                amountField.value = '';
            }
            calculateCompletionAmounts();
        }

        function calculateCompletionAmounts() {
            const collectedAmount = parseFloat(document.getElementById('collectedAmount').value) || 0;
            const dueAmount = parseFloat(document.getElementById('dueAmount').value) || 0;

            // Calculate extra charges
            let extraChargesTotal = 0;
            const extraTax = document.getElementById('completeExtraTax').checked ? (parseFloat(document.getElementById('completeTaxAmount').value) || 0) : 0;
            const extraBank = document.getElementById('completeExtraBank').checked ? (parseFloat(document.getElementById('completeBankAmount').value) || 0) : 0;
            const extraOther = document.getElementById('completeExtraOther').checked ? (parseFloat(document.getElementById('completeOtherAmount').value) || 0) : 0;

            extraChargesTotal = extraTax + extraBank + extraOther;

            const totalRequired = dueAmount + extraChargesTotal;

            // Portions
            // Pay extra charges first, then apply remaining to base due
            let appliedToExtra = Math.min(collectedAmount, extraChargesTotal);
            let remainingForService = Math.max(0, collectedAmount - extraChargesTotal);
            let appliedToService = Math.min(remainingForService, dueAmount);

            const remainingDueOnService = Math.max(0, dueAmount - appliedToService);

            // Update UI
            document.getElementById('finalPaymentDisplay').textContent = `₹${totalRequired.toFixed(2)}`;

            // Visual feedback if underpaid
            const finalPaymentDisplay = document.getElementById('finalPaymentDisplay');
            if (collectedAmount < totalRequired) {
                finalPaymentDisplay.style.color = '#e74c3c'; // Red
            } else {
                finalPaymentDisplay.style.color = '#2ecc71'; // Green
            }

            // Update Dynamic Labels if in Self-Pay
            if (isSelfPayCompletionActive) {
                const colLabel = document.getElementById('collectedAmountLabel');
                const mdeLabel = document.getElementById('duePaymentModeLabel');
                if (colLabel) colLabel.innerHTML = `<i class="fas fa-hand-holding-usd"></i> Total Company Collection (Remaining Amount)`;
                if (mdeLabel) mdeLabel.innerHTML = `<i class="fas fa-question-circle"></i> How do you want to collect this ₹${collectedAmount.toFixed(2)}? *`;
            }
        }

        // ========== TASK MANAGEMENT FUNCTIONS ==========
        async function showCompleteTaskModal(taskId) {
            currentTaskId = taskId;

            try {
                // Fetch latest task details from API
                const response = await apiFetch(`/api/tasks/${taskId}`);
                if (!response.ok) throw new Error('Failed to load task');

                const task = await response.json();

                // Calculate due amount if not set (total_amount - paid_amount)
                const totalAmount = parseFloat(task.total_amount) || parseFloat(task.service_price) || 0;
                const paidAmount = parseFloat(task.paid_amount) || 0;
                const dueAmount = parseFloat(task.due_amount) || (totalAmount - paidAmount);

                // Reset Self-Pay Block UI
                isSelfPayCompletionActive = false;
                const spBlock = document.getElementById('selfPayCollectionBlock');
                const mainCollectionGroup = document.getElementById('mainCollectionGroup');
                if (spBlock) spBlock.style.display = 'none';
                if (mainCollectionGroup) mainCollectionGroup.style.display = 'block';

                // Reset Self-Pay Provider Details
                const spProviderName = document.getElementById('selfPayProviderName');
                const spProviderPhone = document.getElementById('selfPayProviderPhone');
                const spNotes = document.getElementById('selfPayNotes');
                if (spProviderName) spProviderName.value = '';
                if (spProviderPhone) spProviderPhone.value = '';
                if (spNotes) spNotes.value = '';

                document.getElementById('taskAmount').value = totalAmount;
                document.getElementById('paidAmount').value = paidAmount;
                document.getElementById('dueAmount').value = Math.max(0, dueAmount);
                document.getElementById('collectedAmount').value = Math.max(0, dueAmount); // Default to full due

                document.getElementById('totalAmountDisplay').textContent = `₹${totalAmount.toFixed(2)}`;
                document.getElementById('alreadyPaidDisplay').textContent = `₹${paidAmount.toFixed(2)}`;
                document.getElementById('dueAmountDisplay').textContent = `₹${dueAmount.toFixed(2)}`;
                document.getElementById('finalPaymentDisplay').textContent = `₹${dueAmount.toFixed(2)}`;

                // Reset labels
                const colLabel = document.getElementById('collectedAmountLabel');
                const mdeLabel = document.getElementById('duePaymentModeLabel');
                if (colLabel) colLabel.textContent = "💰 Amount to Collect Now (including extra charges)";
                if (mdeLabel) mdeLabel.textContent = "Payment Mode for Due Amount *";

                // Reset completion notes
                document.getElementById('completionNotes').value = '';

                // Reset extra charges and add listeners
                const extraChargeConfigs = [
                    { chk: 'completeExtraTax', amt: 'completeTaxAmount' },
                    { chk: 'completeExtraBank', amt: 'completeBankAmount' },
                    { chk: 'completeExtraOther', amt: 'completeOtherAmount' }
                ];

                extraChargeConfigs.forEach(config => {
                    const checkbox = document.getElementById(config.chk);
                    const amountInput = document.getElementById(config.amt);

                    if (checkbox) {
                        checkbox.checked = false;
                        checkbox.onclick = toggleExtraChargeAmount;
                    }
                    if (amountInput) {
                        amountInput.value = '';
                        amountInput.disabled = true;
                        amountInput.oninput = calculateCompletionAmounts;
                    }
                });

                // Reset payment mode
                const duePaymentMode = document.getElementById('duePaymentMode');
                const serviceFeeVal = parseFloat(task.service_fee) || 0; // service_fee = govt fee

                if (duePaymentMode) {
                    duePaymentMode.value = '';
                    duePaymentMode.required = false;

                    // Logic to hide 'self_pay' if task is already 'self_pay' OR if due < govt fee
                    for (let i = 0; i < duePaymentMode.options.length; i++) {
                        if (duePaymentMode.options[i].value === 'self_pay') {
                            if (task.is_self_pay || dueAmount < serviceFeeVal) {
                                duePaymentMode.options[i].style.display = 'none';
                            } else {
                                duePaymentMode.options[i].style.display = 'block';
                            }
                        }
                    }
                }

                const duePaymentModeSection = document.getElementById('duePaymentModeSection');
                const completeDueReasonContainer = document.getElementById('completeDueReasonContainer');
                if (dueAmount > 0) {
                    if (duePaymentModeSection) {
                        duePaymentModeSection.style.display = 'block';
                        if (duePaymentMode) duePaymentMode.required = true;
                    }
                    if (completeDueReasonContainer) {
                        completeDueReasonContainer.style.display = 'block';
                        // Reset due reason fields
                        const offerRadios = document.querySelectorAll('input[name="completeDueReason"]');
                        if (offerRadios.length) offerRadios.forEach(r => { r.checked = false; });
                        const offerAmt = document.getElementById('completeOfferAmount');
                        if (offerAmt) { offerAmt.value = '0'; offerAmt.required = false; }
                        const completeOfferSection = document.getElementById('completeOfferDetailsSection');
                        if (completeOfferSection) completeOfferSection.style.display = 'none';
                        const completeDueReasonText = document.getElementById('completeDueReasonText');
                        if (completeDueReasonText) completeDueReasonText.value = '';
                    }
                    // Show due amount breakdown with fee info
                    showDueAmountBreakdown(task, dueAmount, totalAmount, paidAmount);
                } else {
                    if (duePaymentModeSection) duePaymentModeSection.style.display = 'none';
                    if (completeDueReasonContainer) completeDueReasonContainer.style.display = 'none';
                    // Hide breakdown if no due amount
                    const breakdown = document.getElementById('dueAmountBreakdown');
                    if (breakdown) breakdown.style.display = 'none';
                }

                // Show/hide Self Pay trigger button - HIDE if due < govt fee
                const selfPayBtn = document.getElementById('selfPayTriggerBtn');
                if (selfPayBtn) {
                    selfPayBtn.style.display = (task.is_self_pay || dueAmount < serviceFeeVal) ? 'none' : 'inline-block';
                }

                // Hide hybrid and self-pay sections
                const hybridSection = document.getElementById('hybridBreakdownSection');
                const selfPaySection = document.getElementById('selfPayConfirmation');
                if (hybridSection) hybridSection.style.display = 'none';
                if (selfPaySection) selfPaySection.style.display = 'none';

                const paymentModeInfo = document.getElementById('paymentModeInfo');
                if (paymentModeInfo) {
                    if (task.payment_mode === 'self_pay') {
                        paymentModeInfo.style.display = 'block';
                    } else {
                        paymentModeInfo.style.display = 'none';
                    }
                }

                showModal('completeTaskModal');
            } catch (error) {
                console.error('Error loading task:', error);
                showToast('Failed to load task details', 'error');
            }
        }

        function calculateSelfPayTotal() {
            const agencyFee = parseFloat(document.getElementById('agencyFeeAmount').value) || 0;
            const additional = parseFloat(document.getElementById('additionalCollectionAmount').value) || 0;
            const total = agencyFee + additional;

            const collectedInput = document.getElementById('collectedAmount');
            if (collectedInput) {
                collectedInput.value = total.toFixed(2);
                calculateCompletionAmounts();
            }
        }

        // Show breakdown of due amount with fee information
        function showDueAmountBreakdown(task, dueAmount, totalAmount, paidAmount) {
            const breakdown = document.getElementById('dueAmountBreakdown');
            if (!breakdown) return;

            const serviceFee = parseFloat(task.service_fee) || 0; // govt fee
            const serviceCharge = parseFloat(task.service_charge) || 0; // company profit
            const servicePrice = parseFloat(task.service_price) || totalAmount; // total price

            let govtFeeInDue, profitInDue;
            // Self-pay from start: company only collects fee; any "due" is uncollected company revenue (full due = company profit)
            if (task.is_self_pay) {
                govtFeeInDue = 0;
                profitInDue = dueAmount.toFixed(2);
            } else {
                // Normal: proportional split of due by fee vs profit
                const paidRatio = servicePrice > 0 ? paidAmount / servicePrice : 0;
                const dueRatio = 1 - paidRatio;
                govtFeeInDue = (serviceFee * dueRatio).toFixed(2);
                profitInDue = (serviceCharge * dueRatio).toFixed(2);
            }

            document.getElementById('breakdownTotalDue').textContent = `₹${dueAmount.toFixed(2)}`;
            document.getElementById('breakdownGovtFee').textContent = `₹${govtFeeInDue}`;
            document.getElementById('breakdownProfit').textContent = `₹${profitInDue}`;

            breakdown.style.display = 'block';

            // Help text: only show self-pay tip when NOT already self-pay (user may choose self-pay for due)
            const helpText = breakdown.querySelector('.help-text') || document.createElement('div');
            helpText.className = 'help-text';
            helpText.style.marginTop = '8px';
            helpText.style.padding = '8px';
            helpText.style.background = '#fff3cd';
            helpText.style.borderRadius = '4px';
            helpText.style.fontSize = '12px';
            if (task.is_self_pay) {
                helpText.innerHTML = `<strong>Self-Pay task:</strong> The due amount (₹${dueAmount.toFixed(2)}) is uncollected company revenue (fee). Govt fee in this due: ₹0.`;
            } else {
                helpText.innerHTML = `
                <strong>💡 Self-Pay Tip:</strong> If you select "Self-Pay", customer pays the provider directly. 
                You only collect the Govt Fee (₹${govtFeeInDue}) from customer.
            `;
            }
            if (!breakdown.querySelector('.help-text')) {
                breakdown.appendChild(helpText);
            } else {
                breakdown.querySelector('.help-text').innerHTML = helpText.innerHTML;
            }
        }

        function handleDuePaymentModeChange() {
            const mode = document.getElementById('duePaymentMode').value;
            const spBlock = document.getElementById('selfPayCollectionBlock');
            const mainCollectionGroup = document.getElementById('mainCollectionGroup');
            const selfPayConfirmation = document.getElementById('selfPayConfirmation');
            const hybridSection = document.getElementById('hybridBreakdownSection');

            if (mode === 'self_pay') {
                triggerSelfPay();
            } else if (mode === 'hybrid') {
                isSelfPayCompletionActive = false;
                if (spBlock) spBlock.style.display = 'none';
                if (mainCollectionGroup) mainCollectionGroup.style.display = 'block';
                if (selfPayConfirmation) selfPayConfirmation.style.display = 'none';
                if (hybridSection) hybridSection.style.display = 'block';

                // Restore standard labels
                const colLabel = document.getElementById('collectedAmountLabel');
                const mdeLabel = document.getElementById('duePaymentModeLabel');
                if (colLabel) colLabel.textContent = "💰 Amount to Collect Now (including extra charges)";
                if (mdeLabel) mdeLabel.textContent = "Payment Mode for Due Amount *";
            } else {
                // Restoration logic for standard payment modes (Cash, UPI, etc.)
                isSelfPayCompletionActive = false;
                if (spBlock) spBlock.style.display = 'none';
                if (mainCollectionGroup) mainCollectionGroup.style.display = 'block';
                if (selfPayConfirmation) selfPayConfirmation.style.display = 'none';
                if (hybridSection) hybridSection.style.display = 'none';

                // Restore standard labels
                const colLabel = document.getElementById('collectedAmountLabel');
                const mdeLabel = document.getElementById('duePaymentModeLabel');
                if (colLabel) colLabel.textContent = "💰 Amount to Collect Now (including extra charges)";
                if (mdeLabel) mdeLabel.textContent = "Payment Mode for Due Amount *";

                // Re-sync collected amount from original due amount
                const dueAmount = parseFloat(document.getElementById('dueAmount').value) || 0;
                const collectedInput = document.getElementById('collectedAmount');
                if (collectedInput) {
                    collectedInput.value = dueAmount.toFixed(2);
                    calculateCompletionAmounts();
                }
            }
        }

        async function triggerSelfPay() {
            if (!currentTaskId) return;
            const task = tasks.find(t => t.id === currentTaskId);
            if (!task) return;

            const fee = parseFloat(task.service_fee) || 0; // service_fee = govt fee

            // 1. Activate global self-pay flag
            isSelfPayCompletionActive = true;

            // 2. Show Refined Self-Pay (Blue Block), Hide standard collection input
            const spBlock = document.getElementById('selfPayCollectionBlock');
            const mainCollectionGroup = document.getElementById('mainCollectionGroup');
            if (spBlock) spBlock.style.display = 'block';
            if (mainCollectionGroup) mainCollectionGroup.style.display = 'none';

            // 3. Populate and Lock Govt Agency Fee
            const spFeeInput = document.getElementById('agencyFeeAmount');
            const spAddInput = document.getElementById('additionalCollectionAmount');
            const spAddMode = document.getElementById('additionalCollectionMode');
            if (spFeeInput) spFeeInput.value = fee.toFixed(2);
            // Don't reset additional values if they was already set? Actually better to reset for fresh start
            // if (spAddInput) spAddInput.value = ''; 

            // 4. Force Show the yellow confirmation box (Provider info)
            const selfPaySection = document.getElementById('selfPayConfirmation');
            if (selfPaySection) selfPaySection.style.display = 'block';

            // 5. Update the dynamic header in yellow box
            const header = document.getElementById('selfPayFeeHeader');
            if (header) header.textContent = `Govt Fees Amount: ₹${fee.toFixed(2)}`;

            // 6. Ensure the Payment Mode Selection for Due Amount (Method) is visible
            const duePaymentModeSection = document.getElementById('duePaymentModeSection');
            const duePaymentMode = document.getElementById('duePaymentMode');
            if (duePaymentModeSection) {
                duePaymentModeSection.style.display = 'block';
            }
            if (duePaymentMode && duePaymentMode.value !== 'self_pay') {
                duePaymentMode.value = 'self_pay';
            }

            // 7. Sync with main hidden input
            calculateSelfPayTotal();

            // showToast('Self-pay mode triggered. Please select payment method for the fee.', 'info');
        }

        async function completeTask() {
            if (!currentTaskId) {
                showToast('No task selected', 'error');
                return;
            }

            const completionNotes = document.getElementById('completionNotes').value || '';
            const paymentMode = document.getElementById('duePaymentMode').value;
            const collectedAmount = parseFloat(document.getElementById('collectedAmount').value) || 0;

            // Get task details
            const task = tasks.find(t => t.id === currentTaskId);
            if (!task) {
                showToast('Task not found', 'error');
                return;
            }

            const totalAmount = parseFloat(task.total_amount) || parseFloat(task.service_price) || 0;
            const alreadyPaid = parseFloat(task.paid_amount) || 0;
            const baseDueAmount = totalAmount - alreadyPaid;

            // Calculate extras
            const extraTax = document.getElementById('completeExtraTax').checked ? (parseFloat(document.getElementById('completeTaxAmount').value) || 0) : 0;
            const extraBank = document.getElementById('completeExtraBank').checked ? (parseFloat(document.getElementById('completeBankAmount').value) || 0) : 0;
            const extraOther = document.getElementById('completeExtraOther').checked ? (parseFloat(document.getElementById('completeOtherAmount').value) || 0) : 0;
            const extraChargesTotal = extraTax + extraBank + extraOther;

            // Allocation logic: Extra charges are settled first
            const amountAppliedToService = Math.max(0, collectedAmount - extraChargesTotal);
            const remainingDueOnService = Math.max(0, baseDueAmount - amountAppliedToService);

            // If there's remaining due on the service, require reason from the due-reason block
            let dueReason = '';
            let dueReasonType = '';
            let offerAmount = 0;
            if (remainingDueOnService > 0.01) {
                const dueReasonContainer = document.getElementById('completeDueReasonContainer');
                if (dueReasonContainer && dueReasonContainer.style.display !== 'none') {
                    const chosen = document.querySelector('input[name="completeDueReason"]:checked');
                    if (!chosen) {
                        showToast('Please select a due reason type (Offer/Discount, Payment Plan, or Other)', 'error');
                        return;
                    }
                    dueReasonType = chosen.value;
                    const reasonText = (document.getElementById('completeDueReasonText') || {}).value || '';
                    if (!reasonText.trim()) {
                        showToast('Please explain the reason for the due amount', 'error');
                        return;
                    }
                    dueReason = reasonText.trim();
                    if (dueReasonType === 'offer') {
                        offerAmount = parseFloat(document.getElementById('completeOfferAmount')?.value) || 0;
                        if (offerAmount <= 0) {
                            showToast('Please enter Offer/Discount amount', 'error');
                            return;
                        }
                    }
                } else {
                    showToast('Please provide a reason for remaining due amount', 'warning');
                    return;
                }
            }

            // Validate payment mode if payment amount > 0
            if (collectedAmount > 0 && !paymentMode) {
                showToast('Please select payment mode', 'error');
                return;
            }

            // Collect extra charges
            const extraCharges = {};
            if (document.getElementById('completeExtraTax') && document.getElementById('completeExtraTax').checked) {
                extraCharges.tax = parseFloat(document.getElementById('completeTaxAmount').value) || 0;
            }
            if (document.getElementById('completeExtraBank') && document.getElementById('completeExtraBank').checked) {
                extraCharges.bank = parseFloat(document.getElementById('completeBankAmount').value) || 0;
            }
            if (document.getElementById('completeExtraOther') && document.getElementById('completeExtraOther').checked) {
                extraCharges.other = parseFloat(document.getElementById('completeOtherAmount').value) || 0;
            }

            try {
                const response = await apiFetch(`/api/tasks/${currentTaskId}/complete`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        completion_notes: completionNotes,
                        payment_amount: collectedAmount, // Total collected including extras
                        collected_amount: collectedAmount,
                        payment_mode: paymentMode || 'cash',
                        extra_charges: extraCharges,
                        due_reason: dueReason,
                        due_reason_type: dueReasonType,
                        offer_amount: offerAmount,
                        remaining_due: remainingDueOnService,
                        is_self_pay: isSelfPayCompletionActive || paymentMode === 'self_pay',
                        provider_name: document.getElementById('selfPayProviderName')?.value || '',
                        provider_phone: document.getElementById('selfPayProviderPhone')?.value || '',
                        other_amount: parseFloat(document.getElementById('additionalCollectionAmount')?.value) || 0,
                        other_amount_mode: document.getElementById('additionalCollectionMode')?.value || 'cash'
                    })
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast('Task completed successfully!', 'success');
                    closeModal('completeTaskModal');
                    loadTasks();
                    loadStatistics();
                } else {
                    showToast(result.error || 'Failed to complete task', 'error');
                }
            } catch (error) {
                console.error('Error completing task:', error);
                showToast('Error completing task: ' + error.message, 'error');
            }
        }

        function showHoldTaskModal(taskId) {
            currentTaskId = taskId;
            showModal('holdTaskModal');
        }

        async function confirmHoldTask() {
            if (!currentTaskId) {
                showToast('No task selected', 'error');
                return;
            }

            const selectedReason = document.querySelector('.hold-reason.selected');
            if (!selectedReason) {
                showToast('Please select a reason for hold', 'error');
                return;
            }

            let reason = selectedReason.dataset.reason;
            if (reason === 'other') {
                reason = document.getElementById('otherHoldReason').value;
                if (!reason) {
                    showToast('Please specify the reason', 'error');
                    return;
                }
            }

            const notes = document.getElementById('holdNotes').value || '';
            const estimatedResumeDate = document.getElementById('estimatedResumeDate').value;
            const paidAmount = parseFloat(document.getElementById('holdPaidAmount').value) || 0;
            const paymentMode = document.getElementById('holdPaymentMode').value;

            try {
                const response = await apiFetch(`/api/tasks/${currentTaskId}/hold`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        reason: reason,
                        notes: notes,
                        estimated_resume_date: estimatedResumeDate,
                        paid_amount: paidAmount,
                        payment_mode: paymentMode
                    })
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast('Task put on hold successfully!', 'success');
                    closeModal('holdTaskModal');
                    loadTasks();
                } else {
                    showToast(result.error || 'Failed to put task on hold', 'error');
                }
            } catch (error) {
                console.error('Error holding task:', error);
                showToast('Error holding task: ' + error.message, 'error');
            }
        }

        async function showStatusChangeModal(taskId) {
            currentTaskId = taskId;

            try {
                // Fetch fresh task data
                const response = await apiFetch(`/api/tasks/${taskId}`);
                if (response.ok) {
                    const task = await response.json();

                    // Set current status
                    const statusSelect = document.getElementById('newStatus');
                    if (statusSelect) {
                        statusSelect.value = task.status;
                    }

                    // Show modal
                    showModal('changeStatusModal');

                    // logic to hide self pay if already self pay OR if due < govt fee
                    const paymentModeSelect = document.getElementById('statusPaymentMode');
                    const totalAmount = parseFloat(task.total_amount) || parseFloat(task.service_price) || 0;
                    const paidAmount = parseFloat(task.paid_amount) || 0;
                    const dueAmount = totalAmount - paidAmount;
                    const serviceFeeVal = parseFloat(task.service_fee) || 0; // service_fee = govt fee

                    if (paymentModeSelect) {
                        for (let i = 0; i < paymentModeSelect.options.length; i++) {
                            if (paymentModeSelect.options[i].value === 'self_pay') {
                                if (task.is_self_pay || dueAmount < serviceFeeVal) {
                                    paymentModeSelect.options[i].style.display = 'none';
                                } else {
                                    paymentModeSelect.options[i].style.display = 'block';
                                }
                            }
                        }
                    }

                    // Trigger change handler to set initial state
                    handleStatusChange();
                } else {
                    showToast('Failed to load task details', 'error');
                }
            } catch (error) {
                console.error('Error loading task for status change:', error);
                showToast('Error loading task details', 'error');
            }
        }

        function handleStatusChange() {
            const newStatus = document.getElementById('newStatus').value;
            const paymentContainer = document.getElementById('paymentAmountContainer');

            if (newStatus === 'completed') {
                // If completed is selected, switch to the dedicated complete task modal
                closeModal('changeStatusModal');
                showCompleteTaskModal(currentTaskId);
                return;
            }

            if (paymentContainer) {
                paymentContainer.style.display = 'none';
            }
        }

        function handleStatusPaymentModeChange() {
            const mode = document.getElementById('statusPaymentMode').value;
            const amountInput = document.getElementById('statusPaymentAmount');

            if (mode === 'self_pay' && currentTaskId) {
                const task = tasks.find(t => t.id === currentTaskId);
                if (task) {
                    const fee = task.service_fee || 0; // service_fee = govt fee
                    amountInput.value = fee;
                    amountInput.readOnly = true;
                }
            } else {
                amountInput.readOnly = false;
            }
        }

        async function confirmStatusChange(taskId) {
            console.log('confirmStatusChange called', { taskId, currentTaskId });
            const tid = taskId || currentTaskId;
            if (!tid) {
                showToast('No task selected', 'error');
                return;
            }

            const newStatusEl = document.getElementById('newStatus');
            const newStatus = newStatusEl ? newStatusEl.value : null;
            const reasonEl = document.getElementById('statusChangeReason') || document.getElementById('statusReason');
            const reason = reasonEl ? reasonEl.value : '';

            if (!newStatus) {
                showToast('Please select a new status', 'error');
                return;
            }

            if (!reason || !reason.trim()) {
                showToast('Please provide a reason for the status change', 'error');
                return;
            }

            let paymentAmount = 0;
            let paymentMode = '';
            let extraCharges = {};
            let offerData = null;

            if (newStatus === 'completed') {
                paymentAmount = parseFloat(document.getElementById('statusPaymentAmount')?.value) || 0;
                paymentMode = document.getElementById('statusPaymentMode')?.value || '';

                if (!paymentMode && paymentAmount > 0) {
                    showToast('Please select payment mode', 'error');
                    return;
                }

                // Collect extra charges (these are NOT added to due amount)
                if (document.getElementById('statusExtraTax')?.checked) {
                    extraCharges.tax = parseFloat(document.getElementById('statusTaxAmount')?.value) || 0;
                }
                if (document.getElementById('statusExtraBank')?.checked) {
                    extraCharges.bank = parseFloat(document.getElementById('statusBankAmount')?.value) || 0;
                }
                if (document.getElementById('statusExtraOther')?.checked) {
                    extraCharges.other = parseFloat(document.getElementById('statusOtherAmount')?.value) || 0;
                }

                // Check if due reason section is visible (meaning there's a due amount)
                const dueReasonContainer = document.getElementById('dueReasonContainer');
                if (dueReasonContainer && dueReasonContainer.style.display !== 'none') {
                    const selectedDueReason = document.querySelector('input[name="dueReason"]:checked');
                    const dueReasonText = document.getElementById('dueReasonText')?.value;

                    if (!selectedDueReason) {
                        showToast('Please select a reason for the due amount', 'error');
                        return;
                    }

                    if (!dueReasonText || !dueReasonText.trim()) {
                        showToast('Please explain the reason for the due amount', 'error');
                        return;
                    }

                    offerData = {
                        is_offer: selectedDueReason.value === 'offer',
                        offer_reason: dueReasonText,
                        offer_amount: selectedDueReason.value === 'offer' ?
                            (parseFloat(document.getElementById('offerAmount')?.value) || 0) : 0
                    };
                }
            }

            const btn = document.getElementById('confirmStatusBtn');
            const originalText = btn ? btn.innerHTML : null;
            try {
                if (btn) {
                    btn.disabled = true;
                    btn.innerHTML = 'Updating...';
                }

                const requestBody = {
                    status: newStatus,
                    reason: reason,
                    payment_amount: paymentAmount,
                    payment_mode: paymentMode,
                    extra_charges: extraCharges,
                    changed_by: document.getElementById('currentUsername')?.value || ''
                };

                // Add offer data if present
                if (offerData) {
                    requestBody.is_offer = offerData.is_offer;
                    requestBody.offer_reason = offerData.offer_reason;
                    requestBody.offer_amount = offerData.offer_amount;
                }

                const response = await apiFetch(`/api/tasks/${tid}/status`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestBody)
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast('Task status updated successfully!', 'success');
                    closeModal('changeStatusModal');
                    loadTasks();
                } else {
                    console.error('Status update failed', result);
                    showToast(result.error || 'Failed to update task status', 'error');
                }
            } catch (error) {
                console.error('Error updating task status:', error);
                showToast('Error updating task status: ' + error.message, 'error');
            } finally {
                if (btn) {
                    btn.disabled = false;
                    if (originalText) btn.innerHTML = originalText;
                }
            }
        }

        // ========== TASK CANCELLATION FUNCTIONS ==========
        function showCancelTaskModal(taskId) {
            currentTaskId = taskId;

            const modalContent = `
            <div class="cancel-task-modal">
                <div class="form-group">
                    <label for="cancelReason"><i class="fas fa-exclamation-triangle"></i> Reason for Cancellation *</label>
                    <textarea id="cancelReason" class="form-control" rows="3" placeholder="Why are you cancelling this task?" required></textarea>
                </div>
                <div class="form-group">
                    <label for="refundAmount"><i class="fas fa-money-bill-wave"></i> Refund Amount (if any)</label>
                    <input type="number" id="refundAmount" class="form-control" placeholder="Enter refund amount" min="0">
                </div>
                <div class="form-group">
                    <label for="refundMode"><i class="fas fa-credit-card"></i> Refund Mode</label>
                    <select id="refundMode" class="form-control">
                        <option value="">Select Refund Mode</option>
                        <option value="cash">Cash</option>
                        <option value="bank_transfer">Bank Transfer</option>
                        <option value="upi">UPI</option>
                        <option value="credit_note">Credit Note</option>
                        <option value="none">No Refund</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="cancelNotes"><i class="fas fa-sticky-note"></i> Additional Notes</label>
                    <textarea id="cancelNotes" class="form-control" rows="2" placeholder="Any additional information..."></textarea>
                </div>
            </div>
        `;

            showCustomModal('Cancel Task', modalContent, [
                {
                    text: 'Cancel',
                    class: 'btn-secondary',
                    action: 'close'
                },
                {
                    text: 'Confirm Cancellation',
                    class: 'btn-danger',
                    action: () => confirmCancelTask()
                }
            ]);
        }

        async function confirmCancelTask() {
            if (!currentTaskId) {
                showToast('No task selected', 'error');
                return;
            }

            const reason = document.getElementById('cancelReason').value;
            if (!reason || !reason.trim()) {
                showToast('Please provide a reason for cancellation', 'error');
                return;
            }

            const refundAmount = parseFloat(document.getElementById('refundAmount').value) || 0;
            const refundMode = document.getElementById('refundMode').value;
            const notes = document.getElementById('cancelNotes').value || '';

            if (refundAmount > 0 && !refundMode) {
                showToast('Please select refund mode if refunding amount', 'warning');
                return;
            }

            try {
                const response = await apiFetch(`/api/tasks/${currentTaskId}/cancel`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        reason: reason,
                        refund_amount: refundAmount,
                        refund_mode: refundMode,
                        notes: notes,
                        cancelled_by: document.getElementById('currentUsername').value || ''
                    })
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast('Task cancelled successfully!', 'success');
                    closeCustomModal();
                    loadTasks();
                } else {
                    showToast(result.error || 'Failed to cancel task', 'error');
                }
            } catch (error) {
                console.error('Error cancelling task:', error);
                showToast('Error cancelling task: ' + error.message, 'error');
            }
        }

        async function reopenCompletedTask(taskId) {
            if (!taskId) {
                showToast('No task selected', 'error');
                return;
            }

            try {
                const response = await apiFetch(`/api/tasks/${taskId}/reopen`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({})
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast('Task reopened successfully!', 'success');
                    loadTasks();
                    loadStatistics();
                } else {
                    showToast(result.error || 'Failed to reopen task', 'error');
                }
            } catch (error) {
                console.error('Error reopening task:', error);
                showToast('Error reopening task: ' + error.message, 'error');
            }
        }

        // ========== TASK DELETE FUNCTION (ADMIN ONLY) ==========
        async function deleteTask(taskId) {
            if (!canUserDeleteTask()) {
                showToast('Only administrators can delete tasks. You can cancel tasks instead.', 'error');
                showCancelTaskModal(taskId);
                return;
            }

            if (!confirm('Are you sure you want to permanently delete this task?\n\nThis action cannot be undone!')) {
                return;
            }

            try {
                const response = await apiFetch(`/api/tasks/${taskId}`, {
                    method: 'DELETE'
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast('Task deleted successfully!', 'success');
                    loadTasks();
                } else {
                    showToast(result.error || 'Failed to delete task', 'error');
                }
            } catch (error) {
                console.error('Error deleting task:', error);
                showToast('Error deleting task: ' + error.message, 'error');
            }
        }

        // ========== CUSTOMER CHAT ACCESS ==========
        function showCustomerChatModal(taskId) {
            const task = tasks.find(t => t.id === taskId);
            if (task) {
                const modalContent = `
                <div class="customer-chat-info">
                    <h4>Customer Chat Details</h4>
                    <div class="info-section">
                        <p><strong>Customer Name:</strong> ${task.customer_name}</p>
                        <p><strong>Phone:</strong> ${task.customer_phone}</p>
                        <p><strong>Order No:</strong> ${task.order_no}</p>
                        <p><strong>Access Password:</strong> ${task.customer_password || 'Not set'}</p>
                    </div>
                    <div class="instructions">
                        <p><i class="fas fa-info-circle"></i> Share the following with customer:</p>
                        <div class="share-box">
                            <p><strong>URL:</strong> /customer/task/${task.id}</p>
                            <p><strong>Password:</strong> ${task.customer_password || 'Not set'}</p>
                            <button class="btn btn-sm btn-copy" onclick="copyChatDetails(${task.id})">
                                <i class="fas fa-copy"></i> Copy Details
                            </button>
                        </div>
                    </div>
                </div>
            `;

                showCustomModal('Customer Chat Access', modalContent);
            }
        }

        function copyChatDetails(taskId) {
            const task = tasks.find(t => t.id === taskId);
            if (task) {
                const details = `URL: /customer/task/${task.id}\nPassword: ${task.customer_password || 'Not set'}`;
                navigator.clipboard.writeText(details).then(() => {
                    showToast('Chat details copied to clipboard!', 'success');
                });
            }
        }

        // ========== STATUS CHANGE WITH NOTIFICATION ==========
        function showStatusChangeWithNotification(taskId) {
            currentTaskId = taskId;
            const task = tasks.find(t => t.id === taskId);

            if (task) {
                const modalContent = `
                <div class="status-change-modal">
                    <div class="form-group">
                        <label for="statusSelect">New Status *</label>
                        <select id="statusSelect" class="form-control">
                            <option value="">Select Status</option>
                            <option value="pending">Pending</option>
                            <option value="in_progress">In Progress</option>
                            <option value="cancelled">Cancelled</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="statusReason">Reason for Change *</label>
                        <textarea id="statusReason" class="form-control" rows="3" placeholder="Why are you changing the status?"></textarea>
                    </div>
                    <div class="form-group">
                        <div class="form-check">
                            <input type="checkbox" id="sendNotification" class="form-check-input">
                            <label class="form-check-label" for="sendNotification">
                                Send notification to customer
                            </label>
                        </div>
                    </div>
                    <div id="notificationSection" style="display: none;">
                        <div class="form-group">
                            <label for="notificationMessage">Notification Message</label>
                            <textarea id="notificationMessage" class="form-control" rows="2" placeholder="Custom message for customer..."></textarea>
                        </div>
                    </div>
                    ${task.due_amount > 0 ? `
                    <div class="payment-section">
                        <h5>Payment Information</h5>
                        <div class="form-row">
                            <div class="form-group col-md-6">
                                <label for="statusNotificationPaymentAmount">Payment Amount (₹)</label>
                                <input type="number" id="statusNotificationPaymentAmount" class="form-control" value="${task.due_amount}">
                            </div>
                            <div class="form-group col-md-6">
                                <label for="statusNotificationPaymentMode">Payment Mode</label>
                                <select id="statusNotificationPaymentMode" class="form-control">
                                    <option value="">Select Mode</option>
                                    <option value="cash">Cash</option>
                                    <option value="card">Card</option>
                                    <option value="upi">UPI</option>
                                    <option value="bank_transfer">Bank Transfer</option>
                                    
                                </select>
                            </div>
                        </div>
                    </div>
                    ` : ''}
                </div>
            `;

                showCustomModal('Change Task Status', modalContent, [
                    {
                        text: 'Cancel',
                        class: 'btn-secondary',
                        action: 'close'
                    },
                    {
                        text: 'Update Status',
                        class: 'btn-primary',
                        action: () => confirmStatusChangeWithNotification()
                    }
                ]);

                document.getElementById('sendNotification').addEventListener('change', function () {
                    document.getElementById('notificationSection').style.display = this.checked ? 'block' : 'none';
                });
            }
        }

        async function confirmStatusChangeWithNotification() {
            const newStatus = document.getElementById('statusSelect').value;
            const reason = document.getElementById('statusReason').value;
            const sendNotification = document.getElementById('sendNotification').checked;
            const notificationMessage = document.getElementById('notificationMessage')?.value || '';
            const paymentAmount = parseFloat(document.getElementById('statusNotificationPaymentAmount')?.value) || 0;
            const paymentMode = document.getElementById('statusNotificationPaymentMode')?.value || '';

            if (!newStatus || !reason) {
                showToast('Please fill all required fields', 'error');
                return;
            }

            if (paymentAmount > 0 && !paymentMode) {
                showToast('Please select a payment mode', 'error');
                return;
            }

            // If status is 'completed' and there's due amount, ask for reason if not fully paid
            if (newStatus === 'completed' && paymentAmount > 0) {
                const task = tasks.find(t => t.id === currentTaskId);
                if (task) {
                    const totalDue = parseFloat(task.due_amount) || 0;
                    const remainingDue = Math.max(0, totalDue - paymentAmount);

                    if (remainingDue > 0) {
                        const dueReason = prompt(`There is ₹${remainingDue} remaining due. Please provide a reason:`, '');
                        if (dueReason === null || !dueReason.trim()) {
                            showToast('Reason is required for remaining due amount', 'error');
                            return;
                        }
                    }
                }
            }

            try {
                const response = await apiFetch(`/api/tasks/${currentTaskId}/status`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        status: newStatus,
                        reason: reason,
                        send_notification: sendNotification,
                        notification_message: notificationMessage,
                        payment_amount: paymentAmount,
                        payment_mode: paymentMode,
                        is_self_pay: paymentMode === 'self_pay'
                    })
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast('Task status updated successfully!', 'success');
                    closeAllModals();
                    loadTasks();
                } else {
                    showToast(result.error || 'Failed to update status', 'error');
                }
            } catch (error) {
                console.error('Error updating status:', error);
                showToast('Error updating status: ' + error.message, 'error');
            }
        }

        // ========== BILL PRINTING ==========
        async function printTaskBill(taskId) {
            try {
                const response = await apiFetch(`/api/tasks/${taskId}/bill`);
                const contentType = (response.headers.get('content-type') || '').toLowerCase();

                if (contentType.includes('application/json')) {
                    const result = await response.json();
                    if (!response.ok || !result.success) {
                        showToast(result.error || 'Failed to generate bill', 'error');
                        return;
                    }
                    const bill = result.bill;
                    const printWindow = window.open('', '_blank');
                    if (!printWindow) {
                        showToast('Unable to open print window. Allow popups.', 'error');
                        return;
                    }
                    printWindow.document.write(result.html || buildBillHtmlFromObject(bill, taskId));
                    printWindow.document.close();
                } else {
                    // Response is likely HTML (e.g., server-rendered bill or an error page). Print it directly.
                    const html = await response.text();
                    const printWindow = window.open('', '_blank');
                    if (!printWindow) {
                        showToast('Unable to open print window. Allow popups.', 'error');
                        return;
                    }
                    printWindow.document.write(html);
                    printWindow.document.close();
                }
            } catch (error) {
                console.error('Error generating bill:', error);
                showToast('Error generating bill: ' + (error.message || error), 'error');
            }
        }

        // Build a simple HTML from bill object when API returns JSON without HTML
        function buildBillHtmlFromObject(bill, taskId) {
            try {
                const invoiceNumber = bill.invoice_number || taskId || '';
                const invoiceDate = bill.invoice_date || new Date().toLocaleString();
                const customerName = bill.customer_name || '';
                const branch = bill.branch_name || '';
                const rows = (bill.extra_charges || []).map(c => `<tr><td>${escapeHtml(c.type)}</td><td>${escapeHtml(c.description || '')}</td><td style="text-align:right">${c.amount}</td></tr>`).join('');
                return `<!doctype html><html><head><meta charset="utf-8"><title>Invoice ${escapeHtml(invoiceNumber)}</title><style>body{font-family:Arial;padding:18px}table{width:100%;border-collapse:collapse}td,th{padding:8px;border:1px solid #ddd}</style></head><body><h2>Invoice ${escapeHtml(invoiceNumber)}</h2><div>Date: ${escapeHtml(invoiceDate)}</div><div>Customer: ${escapeHtml(customerName)}</div><div>Branch: ${escapeHtml(branch)}</div><h3>Items</h3><table><tr><th>Item</th><th>Description</th><th style="text-align:right">Amount</th></tr>${rows}</table><div style="margin-top:16px">Total: ${escapeHtml(String((bill.totals && bill.totals.grand_total) || ''))}</div><div class="no-print" style="margin-top:18px"><button onclick="window.print()">Print</button></div></body></html>`;
            } catch (e) {
                return '<html><body><pre>' + escapeHtml(JSON.stringify(bill)) + '</pre></body></html>';
            }
        }

        // ========== BILL PDF / SHARE HELPERS ==========
        // Ensure a remote library is loaded and available
        function ensureLibraryLoaded(src, globalVar) {
            return new Promise((resolve, reject) => {
                if (window[globalVar]) return resolve();
                const script = document.createElement('script');
                script.src = src;
                script.async = true;
                script.onload = () => setTimeout(resolve, 50);
                script.onerror = () => reject(new Error('Failed to load ' + src));
                document.head.appendChild(script);
            });
        }

        // Create PDF from HTML using html2canvas + jsPDF (dynamically load libs if needed)
        async function generatePdfFromHtml(htmlContent, filename = 'invoice.pdf') {
            await ensureLibraryLoaded('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js', 'html2canvas');
            await ensureLibraryLoaded('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js', 'jspdf');

            return new Promise((resolve, reject) => {
                const container = document.createElement('div');
                container.style.position = 'fixed';
                container.style.left = '-9999px';
                container.innerHTML = htmlContent;
                document.body.appendChild(container);

                window.html2canvas(container, { scale: 2 }).then(canvas => {
                    const imgData = canvas.toDataURL('image/png');
                    const { jsPDF } = window.jspdf;
                    const pdf = new jsPDF({ unit: 'pt', format: 'a4' });
                    const pageWidth = pdf.internal.pageSize.getWidth();
                    const imgWidth = pageWidth;
                    const imgHeight = (canvas.height * imgWidth) / canvas.width;

                    let position = 0;
                    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
                    if (imgHeight > pdf.internal.pageSize.getHeight()) {
                        let remaining = imgHeight - pdf.internal.pageSize.getHeight();
                        while (remaining > 0) {
                            position = position - pdf.internal.pageSize.getHeight();
                            pdf.addPage();
                            pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
                            remaining -= pdf.internal.pageSize.getHeight();
                        }
                    }

                    pdf.save(filename);
                    document.body.removeChild(container);
                    resolve();
                }).catch(err => {
                    document.body.removeChild(container);
                    reject(err);
                });
            });
        }

        // Share invoice via WhatsApp (text or PDF)
        async function shareBillWhatsApp(taskId, mode = 'text') {
            try {
                const resp = await apiFetch(`/api/tasks/${taskId}/bill`);
                const contentType = (resp.headers.get('content-type') || '').toLowerCase();

                if (mode === 'text') {
                    if (contentType.includes('application/json')) {
                        const data = await resp.json();
                        if (!resp.ok || !data.success) {
                            showToast('Unable to fetch bill for sharing', 'error');
                            return;
                        }
                        const bill = data.bill;
                        const lines = [];
                        lines.push('Invoice: ' + (bill.invoice_number || ''));
                        lines.push('Date: ' + (bill.invoice_date || ''));
                        lines.push('Customer: ' + (bill.customer_name || ''));
                        lines.push('\nServices:');
                        if (bill.service_name) lines.push(`- ${bill.service_name}: ${bill.service_details?.service_charge || ''}`);
                        if (bill.extra_charges && bill.extra_charges.length) {
                            lines.push('\nExtra Charges:');
                            bill.extra_charges.forEach(c => lines.push(`- ${c.type}: ${c.amount}`));
                        }
                        lines.push('\nTotal: ' + (bill.totals ? bill.totals.grand_total : ''));
                        const text = lines.join('\n');
                        const url = 'https://wa.me/?text=' + encodeURIComponent(text);
                        window.open(url, '_blank');
                    } else {
                        // server returned HTML (or other text) — extract visible text
                        const txt = await resp.text();
                        const div = document.createElement('div');
                        div.innerHTML = txt;
                        const visible = div.innerText || div.textContent || txt;
                        const url = 'https://wa.me/?text=' + encodeURIComponent(visible);
                        window.open(url, '_blank');
                    }
                } else if (mode === 'pdf') {
                    if (contentType.includes('application/json')) {
                        const data = await resp.json();
                        if (!resp.ok || !data.success) {
                            showToast('Unable to fetch bill for sharing', 'error');
                            return;
                        }
                        const bill = data.bill;
                        const printHtml = buildBillHtmlFromObject(bill, taskId);
                        const filename = `invoice_${taskId || 'invoice'}.pdf`;
                        await generatePdfFromHtml(printHtml, filename);
                        const msg = `Invoice ${bill.invoice_number || taskId} downloaded. Please attach the PDF file to send.`;
                        window.open('https://wa.me/?text=' + encodeURIComponent(msg), '_blank');
                    } else {
                        // server returned HTML; use it directly to make PDF
                        const html = await resp.text();
                        const filename = `invoice_${taskId || 'invoice'}.pdf`;
                        await generatePdfFromHtml(html, filename);
                        const msg = `Invoice ${taskId} downloaded. Please attach the PDF file to send.`;
                        window.open('https://wa.me/?text=' + encodeURIComponent(msg), '_blank');
                    }
                }
            } catch (err) {
                console.error('Share error', err);
                showToast('Error sharing invoice: ' + (err.message || err), 'error');
            }
        }

        // small escaper used above
        function escapeHtml(str) {
            if (str === null || str === undefined) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        // ========== UTILITY FUNCTIONS ==========
        function formatDate(dateString) {
            if (!dateString) return 'N/A';
            try {
                const date = new Date(dateString);
                return date.toLocaleDateString('en-IN', {
                    day: '2-digit',
                    month: 'short',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            } catch (e) {
                return dateString;
            }
        }

        function formatStatus(status) {
            const statusMap = {
                'pending': 'Pending',
                'in_progress': 'In Progress',
                'in_openplace': 'Open Place',
                'on_hold': 'On Hold',
                'completed': 'Completed',
                'cancelled': 'Cancelled'
            };
            return statusMap[status] || status;
        }

        function formatPriority(priority) {
            const priorityMap = {
                'low': 'Low',
                'medium': 'Medium',
                'high': 'High',
                'urgent': 'Urgent'
            };
            return priorityMap[priority] || 'Medium';
        }

        function formatPaymentMode(mode) {
            const modeMap = {
                'cash': 'Cash',
                'card': 'Card',
                'upi': 'UPI',
                'online': 'Online',
                'bank_transfer': 'Bank Transfer',
                'cheque': 'Cheque',
                'wallet': 'Wallet',
                'self_pay': 'Self-Pay',
                'hybrid': 'Hybrid'
            };
            return modeMap[mode] || mode;
        }

        function formatTimeAgo(dateString) {
            if (!dateString) return '';
            try {
                const date = new Date(dateString);
                const now = new Date();
                const diffMs = now - date;
                const diffMins = Math.floor(diffMs / 60000);

                if (diffMins < 60) {
                    return `${diffMins}m ago`;
                } else if (diffMins < 1440) {
                    const diffHours = Math.floor(diffMins / 60);
                    return `${diffHours}h ago`;
                } else {
                    const diffDays = Math.floor(diffMins / 1440);
                    return `${diffDays}d ago`;
                }
            } catch (e) {
                return '';
            }
        }

        function getInitials(name) {
            return name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
        }

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

        function showLoading() {
            const loading = document.createElement('div');
            loading.id = 'loadingIndicator';
            loading.innerHTML = '<div class="spinner"></div>';
            loading.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
            background: rgba(0,0,0,0.3); display: flex; align-items: center; 
            justify-content: center; z-index: 9999;
        `;
            document.body.appendChild(loading);
        }

        function hideLoading() {
            const loading = document.getElementById('loadingIndicator');
            if (loading) {
                loading.remove();
            }
        }

        function showToast(message, type = 'success') {
            const toast = document.getElementById('toast');
            const toastMessage = document.getElementById('toastMessage');

            if (toast && toastMessage) {
                toastMessage.textContent = message;

                toast.className = 'toast';
                if (type === 'error') {
                    toast.classList.add('error');
                } else if (type === 'warning') {
                    toast.classList.add('warning');
                } else if (type === 'info') {
                    toast.classList.add('info');
                }

                toast.style.display = 'flex';

                setTimeout(() => {
                    toast.style.display = 'none';
                }, 3000);
            }
        }

        function updateUserInfo() {
            const sidebarUserName = document.getElementById('sidebarUserName');
            if (sidebarUserName) {
                sidebarUserName.textContent = document.getElementById('currentUserName').value || 'Guest';
            }
        }

        function updateTableTitle() {
            const titles = {
                'today': "Today's Tasks",
                'pending': "Pending Tasks",
                'critical': "Critical Pending Tasks",
                'cancelled': "Cancelled Tasks",
                'inprogress': "In Progress Tasks",
                'hold': "On Hold Tasks",
                'openplace': "Open Place Tasks",
                'all': "All Tasks"
            };
            const tableTitle = document.getElementById('tableTitle');
            if (tableTitle) {
                tableTitle.textContent = titles[currentTab] || 'Tasks';
            }

            const tableSubtitle = document.getElementById('tableSubtitle');
            if (tableSubtitle) {
                if (currentTab === 'openplace' || currentTab === 'critical' || currentTab === 'cancelled') {
                    tableSubtitle.textContent = `(${tasks.length} available tasks)`;
                    tableSubtitle.style.display = 'inline';
                } else {
                    tableSubtitle.style.display = 'none';
                }
            }
        }

        // (Nav-tab handlers are attached during initialization in initEventListeners)

        function searchTasks() {
            const searchTerm = document.getElementById('taskSearch').value.toLowerCase();
            const tableBody = document.getElementById('taskTableBody');

            if (!tableBody) return;

            const rows = tableBody.querySelectorAll('tr');
            let hasVisibleRows = false;

            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    row.style.display = '';
                    hasVisibleRows = true;
                } else {
                    row.style.display = 'none';
                }
            });

            const emptyState = document.getElementById('emptyState');
            if (emptyState) {
                if (!hasVisibleRows && searchTerm) {
                    emptyState.style.display = 'block';
                    document.getElementById('emptyStateMessage').textContent = 'No tasks match your search.';
                } else {
                    emptyState.style.display = 'none';
                }
            }
        }

        function showFilterOptions() {
            const content = `
            <div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="filterBranch">Branch</label>
                        <select id="filterBranch" class="form-control">
                            <option value="">-- Any Branch --</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="filterStaff">Staff</label>
                        <select id="filterStaff" class="form-control">
                            <option value="">-- Any Staff --</option>
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="filterStatus">Status</label>
                        <select id="filterStatus" class="form-control">
                            <option value="">-- Any Status --</option>
                            <option value="pending">Pending</option>
                            <option value="in_progress">In Progress</option>
                            <option value="on_hold">On Hold</option>
                            <option value="completed">Completed</option>
                            <option value="cancelled">Cancelled</option>
                            <option value="in_openplace">Open Place</option>
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="filterPriority">Priority</label>
                        <select id="filterPriority" class="form-control">
                            <option value="">-- Any Priority --</option>
                            <option value="urgent">Urgent</option>
                            <option value="high">High</option>
                            <option value="medium">Medium</option>
                            <option value="low">Low</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="filterServiceType">Service Type</label>
                        <select id="filterServiceType" class="form-control">
                            <option value="">-- All Types --</option>
                            <option value="normal">Normal Service</option>
                            <option value="business">Business Service</option>
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="filterFromDate">From Date</label>
                        <input type="date" id="filterFromDate" class="form-control">
                    </div>
                    <div class="form-group">
                        <label for="filterToDate">To Date</label>
                        <input type="date" id="filterToDate" class="form-control">
                    </div>
                </div>
                <div style="display:flex; gap:10px; align-items:center; margin-top:10px;">
                    <label style="margin:0; font-weight:600;">Apply To:</label>
                    <select id="filterApplyTo" class="form-control" style="width:180px;">
                        <option value="current">Current Tab</option>
                        <option value="openplace">Open Place</option>
                        <option value="all">All Tasks</option>
                    </select>
                </div>
            </div>
        `;

            // action when user clicks Apply
            async function applyFilterAction() {
                const branch = document.getElementById('filterBranch').value;
                const staff = document.getElementById('filterStaff').value;
                const status = document.getElementById('filterStatus').value;
                const priority = document.getElementById('filterPriority').value;
                const serviceType = document.getElementById('filterServiceType').value;
                const applyTo = document.getElementById('filterApplyTo').value;

                const filters = {};
                if (branch) filters.branch = branch;
                if (staff) filters.staff = staff;
                if (status) filters.status = status;
                if (priority) filters.priority = priority;
                if (serviceType) filters.service_type = serviceType;

                closeCustomModal();

                // decide which loader to call
                if (applyTo === 'openplace' || (applyTo === 'current' && currentTab === 'openplace')) {
                    // use the openplace filter button selection if present
                    const activeBtn = document.querySelector('.openplace-filter-btn.active');
                    const openFilter = activeBtn ? activeBtn.dataset.filter : 'all';
                    await loadOpenPlaceTasks(openFilter, filters);
                } else if (applyTo === 'all') {
                    await loadTasks(filters, 'all');
                } else {
                    // current tab
                    await loadTasks(filters);
                }
            }

            // Close action
            function cancelFilterAction() {
                closeCustomModal();
            }

            showCustomModal('Advanced Filters', content, [
                { text: 'Cancel', class: 'btn-secondary', action: cancelFilterAction },
                { text: 'Apply Filters', class: '', action: applyFilterAction }
            ]);

            // populate branch and staff lists after modal is inserted
            (async function populateLists() {
                try {
                    // fetch branches
                    const bResp = await apiFetch('/api/branches');
                    if (bResp.ok) {
                        const branches = await bResp.json();
                        const sel = document.getElementById('filterBranch');
                        branches.forEach(b => {
                            const opt = document.createElement('option');
                            opt.value = b.id || b.branch_id || b.code || b.name;
                            opt.textContent = b.name || b.branch_name || opt.value;
                            sel.appendChild(opt);
                        });
                    }
                } catch (e) {
                    // ignore
                }

                try {
                    // fetch staff
                    const sResp = await apiFetch('/api/staff');
                    if (sResp.ok) {
                        const staff = await sResp.json();
                        const sel = document.getElementById('filterStaff');
                        staff.forEach(s => {
                            const opt = document.createElement('option');
                            opt.value = s.id || s.username || s.user_id || s.staff_id;
                            opt.textContent = s.name || s.username || s.full_name || opt.value;
                            sel.appendChild(opt);
                        });
                    }
                } catch (e) {
                    // ignore
                }

                // If current user is staff, lock branch and staff to their values
                try {
                    const userRole = document.getElementById('currentUserRole') ? document.getElementById('currentUserRole').value : '';
                    const myBranch = document.getElementById('currentUserBranch') ? document.getElementById('currentUserBranch').value : '';
                    const myUser = document.getElementById('currentUsername') ? document.getElementById('currentUsername').value : '';

                    if (userRole === 'staff') {
                        const branchSel = document.getElementById('filterBranch');
                        if (branchSel) {
                            // ensure option exists
                            if (![...branchSel.options].some(o => String(o.value) === String(myBranch))) {
                                const o = document.createElement('option'); o.value = myBranch; o.textContent = myBranch; branchSel.appendChild(o);
                            }
                            branchSel.value = myBranch;
                            branchSel.disabled = true;
                        }

                        const staffSel = document.getElementById('filterStaff');
                        if (staffSel) {
                            if (![...staffSel.options].some(o => String(o.value) === String(myUser))) {
                                const o = document.createElement('option'); o.value = myUser; o.textContent = myUser; staffSel.appendChild(o);
                            }
                            staffSel.value = myUser;
                            staffSel.disabled = true;
                        }
                    }
                } catch (e) {
                    // ignore
                }
            })();
        }

        function showCustomModal(title, content, buttons = []) {
            const existingModal = document.getElementById('customModal');
            if (existingModal) {
                existingModal.remove();
            }

            const modalHTML = `
            <div class="modal" id="customModal" style="display: flex;">
                <div class="modal-content" style="max-width: 600px;">
                    <div class="modal-header">
                        <h3>${title}</h3>
                        <button class="close-modal" onclick="closeCustomModal()">&times;</button>
                    </div>
                    <div class="modal-body">
                        ${content}
                    </div>
                    <div class="modal-footer">
                        ${buttons.map((btn, index) => `
                            <button class="btn ${btn.class}" id="customModalBtn${index}">
                                ${btn.text}
                            </button>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;

            document.body.insertAdjacentHTML('beforeend', modalHTML);

            // Attach event listeners to buttons
            buttons.forEach((btn, index) => {
                const buttonEl = document.getElementById(`customModalBtn${index}`);
                if (buttonEl) {
                    if (btn.action === 'close') {
                        buttonEl.addEventListener('click', closeCustomModal);
                    } else if (typeof btn.action === 'function') {
                        buttonEl.addEventListener('click', btn.action);
                    } else if (typeof btn.action === 'string') {
                        buttonEl.addEventListener('click', () => {
                            if (typeof window[btn.action] === 'function') {
                                window[btn.action]();
                            } else {
                                eval(btn.action);
                            }
                        });
                    }
                }
            });
        }

        function closeCustomModal() {
            const modal = document.getElementById('customModal');
            if (modal) {
                modal.remove();
            }
        }

        function closeAllModals() {
            document.querySelectorAll('.modal').forEach(modal => {
                if (modal.id !== 'customModal') {
                    modal.style.display = 'none';
                }
            });
            closeCustomModal();
        }

        // ========== MARK AS OFFER ==========
        async function markTaskAsOffer(taskId) {
            const reason = prompt('Enter reason for marking this amount as an offer:');
            if (!reason || reason.trim() === '') {
                showNotification('Offer reason is required', 'error');
                return;
            }

            try {
                const response = await fetch(`/api/tasks/${taskId}/mark-offer`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ reason: reason.trim() })
                });

                const data = await response.json();

                if (data.success) {
                    showNotification('Task marked as offer successfully!', 'success');
                    // Reload tasks to reflect changes
                    await loadMyTasks();
                    closeAllModals();
                }
            } catch (error) {
                console.error('Error marking as offer:', error);
                showNotification('Error marking task as offer', 'error');
            }
        }

        // ========== EXPORT FUNCTIONS TO WINDOW ==========
        window.sendTaskToOpenPlace = sendTaskToOpenPlace;
        window.showTakeTaskModal = showTakeTaskModal;
        window.showStaffAssignmentModal = showStaffAssignmentModal;
        window.selectAssignment = selectAssignment;
        window.viewTaskDetails = viewTaskDetails;
        window.showCompleteTaskModal = showCompleteTaskModal;
        window.showHoldTaskModal = showHoldTaskModal;
        window.showStatusChangeModal = showStatusChangeModal;
        window.deleteTask = deleteTask;
        window.showCancelTaskModal = showCancelTaskModal;
        window.selectService = selectService;
        window.toggleOnlineForm = toggleOnlineForm;
        window.updateSelfPayFields = updateSelfPayFields;
        window.handleDuePaymentModeChange = handleDuePaymentModeChange;
        window.validateHybridPayment = validateHybridPayment;
        window.showCustomerChatModal = showCustomerChatModal;
        window.copyChatDetails = copyChatDetails;
        window.showStatusChangeWithNotification = showStatusChangeWithNotification;
        window.confirmStatusChangeWithNotification = confirmStatusChangeWithNotification;
        window.printTaskBill = printTaskBill;
        window.generatePdfFromHtml = generatePdfFromHtml;
        window.shareBillWhatsApp = shareBillWhatsApp;
        window.editTask = editTask;
        window.reopenCompletedTask = reopenCompletedTask;
        window.markTaskAsOffer = markTaskAsOffer;

        // Export statistics helpers for other scripts/inline callers
        window.updateTaskStatistics = updateTaskStatistics;
        window.updateStatistics = updateStatistics;
        window.updateStatisticsDisplay = updateStatisticsDisplay;
        window.switchTab = switchTab;
    