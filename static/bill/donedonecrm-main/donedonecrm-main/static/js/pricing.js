const paymentsDatabase = {
            user: {
                balance: 1245.50,
                pendingPayments: 245.00,
                totalTransactions: 18,
                currency: "USD"
            },
            paymentMethods: [
                {
                    id: "PM-001",
                    type: "visa",
                    last4: "4321",
                    name: "Visa ending in 4321",
                    expiry: "12/25",
                    isPrimary: true
                },
                {
                    id: "PM-002",
                    type: "mastercard",
                    last4: "8765",
                    name: "Mastercard ending in 8765",
                    expiry: "08/24",
                    isPrimary: false
                },
                {
                    id: "PM-003",
                    type: "paypal",
                    last4: null,
                    name: "PayPal Account",
                    expiry: null,
                    isPrimary: false
                }
            ],
            transactions: [
                {
                    id: "TXN-2023-1001",
                    date: "2023-10-15",
                    description: "Professional License Application - Premium Plan",
                    amount: 300.00,
                    status: "paid",
                    method: "Visa ending in 4321",
                    invoice: "INV-2023-1001"
                },
                {
                    id: "TXN-2023-1002",
                    date: "2023-10-12",
                    description: "Document Verification Service",
                    amount: 90.00,
                    status: "paid",
                    method: "Mastercard ending in 8765",
                    invoice: "INV-2023-1002"
                },
                {
                    id: "TXN-2023-1003",
                    date: "2023-10-10",
                    description: "Business Registration - Professional Plan",
                    amount: 150.00,
                    status: "pending",
                    method: "PayPal Account",
                    invoice: "INV-2023-1003"
                },
                {
                    id: "TXN-2023-1004",
                    date: "2023-10-08",
                    description: "Express Processing Fee",
                    amount: 75.00,
                    status: "paid",
                    method: "Visa ending in 4321",
                    invoice: "INV-2023-1004"
                },
                {
                    id: "TXN-2023-1005",
                    date: "2023-10-05",
                    description: "Annual Subscription Renewal",
                    amount: 199.99,
                    status: "failed",
                    method: "Mastercard ending in 8765",
                    invoice: "INV-2023-1005"
                },
                {
                    id: "TXN-2023-1006",
                    date: "2023-10-01",
                    description: "Service Fee Refund",
                    amount: 50.00,
                    status: "refunded",
                    method: "Visa ending in 4321",
                    invoice: "INV-2023-1006"
                }
            ],
            plans: [
                {
                    id: "plan-1",
                    name: "Basic",
                    price: 75,
                    description: "Standard processing service"
                },
                {
                    id: "plan-2",
                    name: "Professional",
                    price: 150,
                    description: "Express processing with priority support"
                },
                {
                    id: "plan-3",
                    name: "Premium",
                    price: 300,
                    description: "Same-day processing with expert support"
                }
            ]
        };

        // State variables
        let selectedPlan = null;
        let selectedPaymentMethod = paymentsDatabase.paymentMethods.find(method => method.isPrimary);
        let currentTransaction = null;

        // Initialize the page
        document.addEventListener('DOMContentLoaded', function() {
            loadPaymentMethods();
            loadTransactions();
            updateSummary();
            
            // Setup card number formatting
            document.getElementById('cardNumber').addEventListener('input', formatCardNumber);
            document.getElementById('expiryDate').addEventListener('input', formatExpiryDate);
        });

        // Format card number with spaces
        function formatCardNumber(e) {
            let value = e.target.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
            let formatted = '';
            
            for (let i = 0; i < value.length; i++) {
                if (i > 0 && i % 4 === 0) {
                    formatted += ' ';
                }
                formatted += value[i];
            }
            
            e.target.value = formatted.substring(0, 19);
        }

        // Format expiry date as MM/YY
        function formatExpiryDate(e) {
            let value = e.target.value.replace(/[^0-9]/gi, '');
            
            if (value.length >= 2) {
                e.target.value = value.substring(0, 2) + '/' + value.substring(2, 4);
            } else {
                e.target.value = value;
            }
        }

        // Load payment methods
        function loadPaymentMethods() {
            const methodsContainer = document.getElementById('paymentMethods');
            methodsContainer.innerHTML = '';
            
            paymentsDatabase.paymentMethods.forEach(method => {
                const methodCard = document.createElement('div');
                methodCard.className = `method-card ${method.isPrimary ? 'selected' : ''}`;
                methodCard.dataset.id = method.id;
                methodCard.onclick = () => selectPaymentMethod(method.id);
                
                let iconClass = 'fa-credit-card';
                if (method.type === 'visa') iconClass = 'fa-cc-visa';
                if (method.type === 'mastercard') iconClass = 'fa-cc-mastercard';
                if (method.type === 'paypal') iconClass = 'fa-cc-paypal';
                
                methodCard.innerHTML = `
                    <div class="method-icon">
                        <i class="fab ${iconClass}"></i>
                    </div>
                    <div class="method-info">
                        <div class="method-name">${method.name}</div>
                        <div class="method-details">${method.expiry ? `Expires ${method.expiry}` : 'Linked account'}</div>
                    </div>
                    <div class="method-check">
                        <i class="fas fa-check-circle"></i>
                    </div>
                `;
                
                methodsContainer.appendChild(methodCard);
            });
        }

        // Select a payment method
        function selectPaymentMethod(methodId) {
            // Update all method cards
            document.querySelectorAll('.method-card').forEach(card => {
                card.classList.remove('selected');
            });
            
            // Select the clicked card
            const selectedCard = document.querySelector(`.method-card[data-id="${methodId}"]`);
            if (selectedCard) {
                selectedCard.classList.add('selected');
                selectedPaymentMethod = paymentsDatabase.paymentMethods.find(m => m.id === methodId);
                showNotification('Payment method selected', `${selectedPaymentMethod.name} is now your selected payment method`, 'info');
            }
        }

        // Load transactions
        function loadTransactions() {
            const tableBody = document.getElementById('transactionsTableBody');
            tableBody.innerHTML = '';
            
            paymentsDatabase.transactions.forEach(transaction => {
                const row = document.createElement('tr');
                
                // Status badge
                let statusBadge = '';
                if (transaction.status === 'paid') {
                    statusBadge = '<span class="status-badge status-paid">Paid</span>';
                } else if (transaction.status === 'pending') {
                    statusBadge = '<span class="status-badge status-pending">Pending</span>';
                } else if (transaction.status === 'failed') {
                    statusBadge = '<span class="status-badge status-failed">Failed</span>';
                } else if (transaction.status === 'refunded') {
                    statusBadge = '<span class="status-badge status-refunded">Refunded</span>';
                }
                
                // Format date
                const date = new Date(transaction.date);
                const formattedDate = date.toLocaleDateString('en-US', { 
                    year: 'numeric', 
                    month: 'short', 
                    day: 'numeric' 
                });
                
                row.innerHTML = `
                    <td class="transaction-id">${transaction.id}</td>
                    <td>${formattedDate}</td>
                    <td>${transaction.description}</td>
                    <td><strong>$${transaction.amount.toFixed(2)}</strong></td>
                    <td>${statusBadge}</td>
                    <td>
                        <div class="action-buttons">
                            <button class="table-btn" onclick="viewTransaction('${transaction.id}')" title="View Details">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="table-btn" onclick="downloadInvoice('${transaction.invoice}')" title="Download Invoice">
                                <i class="fas fa-download"></i>
                            </button>
                            ${transaction.status === 'pending' ? 
                                `<button class="table-btn" onclick="payTransaction('${transaction.id}')" title="Pay Now">
                                    <i class="fas fa-dollar-sign"></i>
                                </button>` : ''
                            }
                        </div>
                    </td>
                `;
                
                tableBody.appendChild(row);
            });
        }

        // Filter transactions
        function filterTransactions() {
            const filterValue = document.getElementById('transactionFilter').value;
            const rows = document.querySelectorAll('#transactionsTableBody tr');
            
            rows.forEach(row => {
                const status = row.querySelector('.status-badge').textContent.toLowerCase();
                
                if (filterValue === 'all' || status === filterValue) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }

        // Update summary
        function updateSummary() {
            const totalSpent = paymentsDatabase.user.balance;
            const pendingPayments = paymentsDatabase.user.pendingPayments;
            const totalTransactions = paymentsDatabase.transactions.length;
            const paymentMethods = paymentsDatabase.paymentMethods.length;
            
            document.querySelectorAll('.summary-amount')[0].textContent = `$${totalSpent.toFixed(2)}`;
            document.querySelectorAll('.summary-amount')[1].textContent = `$${pendingPayments.toFixed(2)}`;
            document.querySelectorAll('.summary-amount')[2].textContent = totalTransactions;
            document.querySelectorAll('.summary-amount')[3].textContent = paymentMethods;
        }

        // Select a plan
        function selectPlan(planType) {
            const plan = paymentsDatabase.plans.find(p => p.name.toLowerCase() === planType);
            if (plan) {
                selectedPlan = plan;
                showNotification('Plan Selected', `${plan.name} plan has been selected for payment`, 'info');
                
                // Open payment modal with plan details
                makePayment();
                document.getElementById('paymentAmount').value = plan.price;
                document.getElementById('paymentDescription').value = `${plan.name} Plan - ${plan.description}`;
            }
        }

        // View all plans
        function viewAllPlans() {
            showNotification('All Plans', 'Redirecting to complete pricing page...', 'info');
            // In a real app, this would redirect to a full pricing page
        }

        // Make a payment
        function makePayment() {
            const modal = document.getElementById('paymentModal');
            modal.classList.add('active');
            
            // Populate payment methods dropdown
            const methodSelect = document.getElementById('selectPaymentMethod');
            methodSelect.innerHTML = '';
            
            paymentsDatabase.paymentMethods.forEach(method => {
                const option = document.createElement('option');
                option.value = method.id;
                option.textContent = method.name;
                if (method.isPrimary) option.selected = true;
                methodSelect.appendChild(option);
            });
            
            // Update payment details
            const paymentDetails = document.getElementById('paymentDetails');
            const amount = document.getElementById('paymentAmount').value || '0.00';
            const description = document.getElementById('paymentDescription').value || 'Payment for services';
            
            paymentDetails.innerHTML = `
                <div class="payment-item">
                    <span>Description:</span>
                    <span>${description}</span>
                </div>
                <div class="payment-item">
                    <span>Amount:</span>
                    <span>$${parseFloat(amount).toFixed(2)}</span>
                </div>
                <div class="payment-item">
                    <span>Processing Fee:</span>
                    <span>$${(parseFloat(amount) * 0.029 + 0.30).toFixed(2)}</span>
                </div>
                <div class="payment-item">
                    <span>Total:</span>
                    <span>$${(parseFloat(amount) + parseFloat(amount) * 0.029 + 0.30).toFixed(2)}</span>
                </div>
            `;
        }

        // Close payment modal
        function closePaymentModal() {
            document.getElementById('paymentModal').classList.remove('active');
            resetPaymentForm();
        }

        // Process payment
        function processPayment() {
            const amount = parseFloat(document.getElementById('paymentAmount').value);
            const description = document.getElementById('paymentDescription').value;
            const methodId = document.getElementById('selectPaymentMethod').value;
            const saveCard = document.getElementById('saveCard').checked;
            
            if (!amount || amount <= 0) {
                showNotification('Invalid Amount', 'Please enter a valid payment amount', 'error');
                return;
            }
            
            if (!description.trim()) {
                showNotification('Missing Description', 'Please enter a payment description', 'error');
                return;
            }
            
            // Show loading
            document.getElementById('loadingSpinner').classList.add('active');
            
            // Simulate payment processing
            setTimeout(() => {
                // Generate transaction ID
                const transactionId = `TXN-${new Date().getFullYear()}-${String(paymentsDatabase.transactions.length + 1001).padStart(4, '0')}`;
                const invoiceId = `INV-${new Date().getFullYear()}-${String(paymentsDatabase.transactions.length + 1001).padStart(4, '0')}`;
                
                // Find payment method
                const method = paymentsDatabase.paymentMethods.find(m => m.id === methodId);
                
                // Add new transaction
                const newTransaction = {
                    id: transactionId,
                    date: new Date().toISOString().split('T')[0],
                    description: description,
                    amount: amount,
                    status: Math.random() > 0.1 ? 'paid' : 'failed', // 90% success rate
                    method: method.name,
                    invoice: invoiceId
                };
                
                paymentsDatabase.transactions.unshift(newTransaction);
                
                // Update user balance
                if (newTransaction.status === 'paid') {
                    paymentsDatabase.user.balance += amount;
                }
                
                // Reset form and update UI
                document.getElementById('loadingSpinner').classList.remove('active');
                closePaymentModal();
                loadTransactions();
                updateSummary();
                
                // Show success/error message
                if (newTransaction.status === 'paid') {
                    showNotification('Payment Successful', `Your payment of $${amount.toFixed(2)} has been processed successfully`, 'success');
                    
                    // Show invoice
                    setTimeout(() => {
                        viewTransaction(transactionId);
                    }, 1000);
                } else {
                    showNotification('Payment Failed', 'Your payment could not be processed. Please try again.', 'error');
                }
            }, 1500);
        }

        // Reset payment form
        function resetPaymentForm() {
            document.getElementById('paymentAmount').value = '';
            document.getElementById('paymentDescription').value = '';
            document.getElementById('saveCard').checked = false;
            selectedPlan = null;
        }

        // View transaction details
        function viewTransaction(transactionId) {
            const transaction = paymentsDatabase.transactions.find(t => t.id === transactionId);
            if (!transaction) return;
            
            currentTransaction = transaction;
            
            // Show invoice section
            document.getElementById('invoiceSection').style.display = 'block';
            
            // Generate invoice content
            const invoiceContent = document.getElementById('invoiceContent');
            const date = new Date(transaction.date);
            const formattedDate = date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });
            
            invoiceContent.innerHTML = `
                <div class="invoice-header">
                    <div class="invoice-info">
                        <h3>Invoice ${transaction.invoice}</h3>
                        <p class="invoice-id">Transaction ID: ${transaction.id}</p>
                        <p>Date: ${formattedDate}</p>
                        <p>Status: <strong>${transaction.status.toUpperCase()}</strong></p>
                    </div>
                    <div class="invoice-amount">
                        <div class="invoice-total">$${transaction.amount.toFixed(2)}</div>
                        <p>Total Amount</p>
                    </div>
                </div>
                
                <table class="invoice-table">
                    <thead>
                        <tr>
                            <th>Description</th>
                            <th class="text-right">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>${transaction.description}</td>
                            <td class="text-right">$${transaction.amount.toFixed(2)}</td>
                        </tr>
                        <tr>
                            <td>Payment Processing Fee</td>
                            <td class="text-right">$${(transaction.amount * 0.029 + 0.30).toFixed(2)}</td>
                        </tr>
                        <tr style="background: var(--light);">
                            <td><strong>Total</strong></td>
                            <td class="text-right"><strong>$${(transaction.amount + transaction.amount * 0.029 + 0.30).toFixed(2)}</strong></td>
                        </tr>
                    </tbody>
                </table>
                
                <div style="background: var(--light); padding: 20px; border-radius: var(--radius);">
                    <h4 style="margin-bottom: 10px;">Payment Details</h4>
                    <p><strong>Method:</strong> ${transaction.method}</p>
                    <p><strong>Transaction ID:</strong> ${transaction.id}</p>
                    <p><strong>Invoice Number:</strong> ${transaction.invoice}</p>
                </div>
                
                <div style="margin-top: 30px; display: flex; gap: 10px;">
                    <button class="btn btn-primary" onclick="downloadInvoice('${transaction.invoice}')">
                        <i class="fas fa-download"></i> Download Invoice
                    </button>
                    <button class="btn btn-outline" onclick="printInvoice()">
                        <i class="fas fa-print"></i> Print Invoice
                    </button>
                </div>
            `;
            
            // Scroll to invoice section
            document.getElementById('invoiceSection').scrollIntoView({ behavior: 'smooth' });
        }

        // Hide invoice
        function hideInvoice() {
            document.getElementById('invoiceSection').style.display = 'none';
        }

        // Download invoice
        function downloadInvoice(invoiceId) {
            showNotification('Download Started', `Invoice ${invoiceId} is being downloaded`, 'info');
            // In a real app, this would generate and download a PDF
        }

        // Print invoice
        function printInvoice() {
            window.print();
        }

        // Pay a pending transaction
        function payTransaction(transactionId) {
            const transaction = paymentsDatabase.transactions.find(t => t.id === transactionId);
            if (!transaction) return;
            
            // Set up payment modal with transaction details
            makePayment();
            document.getElementById('paymentAmount').value = transaction.amount;
            document.getElementById('paymentDescription').value = `Payment for: ${transaction.description}`;
            
            // Mark this as paying a specific transaction
            currentTransaction = transaction;
        }

        // Add payment method
        function addPaymentMethod() {
            document.getElementById('addMethodModal').classList.add('active');
        }

        // Close add method modal
        function closeAddMethodModal() {
            document.getElementById('addMethodModal').classList.remove('active');
            resetAddMethodForm();
        }

        // Save payment method
        function savePaymentMethod() {
            const cardNumber = document.getElementById('cardNumber').value.replace(/\s+/g, '');
            const expiryDate = document.getElementById('expiryDate').value;
            const cvv = document.getElementById('cvv').value;
            const cardholderName = document.getElementById('cardholderName').value;
            const setAsPrimary = document.getElementById('setAsPrimary').checked;
            
            // Basic validation
            if (cardNumber.length < 16) {
                showNotification('Invalid Card', 'Please enter a valid 16-digit card number', 'error');
                return;
            }
            
            if (!expiryDate.match(/^\d{2}\/\d{2}$/)) {
                showNotification('Invalid Expiry', 'Please enter expiry date in MM/YY format', 'error');
                return;
            }
            
            if (cvv.length < 3) {
                showNotification('Invalid CVV', 'Please enter a valid 3-digit CVV', 'error');
                return;
            }
            
            if (!cardholderName.trim()) {
                showNotification('Missing Name', 'Please enter cardholder name', 'error');
                return;
            }
            
            // Determine card type
            let cardType = 'visa';
            if (cardNumber.startsWith('5')) cardType = 'mastercard';
            
            // Generate new payment method ID
            const methodId = `PM-${String(paymentsDatabase.paymentMethods.length + 1001).padStart(3, '0')}`;
            
            // If setting as primary, update all others
            if (setAsPrimary) {
                paymentsDatabase.paymentMethods.forEach(method => {
                    method.isPrimary = false;
                });
            }
            
            // Add new payment method
            const newMethod = {
                id: methodId,
                type: cardType,
                last4: cardNumber.slice(-4),
                name: `${cardType === 'visa' ? 'Visa' : 'Mastercard'} ending in ${cardNumber.slice(-4)}`,
                expiry: expiryDate,
                isPrimary: setAsPrimary || paymentsDatabase.paymentMethods.length === 0
            };
            
            paymentsDatabase.paymentMethods.push(newMethod);
            
            // Reset form and update UI
            closeAddMethodModal();
            loadPaymentMethods();
            updateSummary();
            
            showNotification('Payment Method Added', 'Your new payment method has been added successfully', 'success');
        }

        // Reset add method form
        function resetAddMethodForm() {
            document.getElementById('cardNumber').value = '';
            document.getElementById('expiryDate').value = '';
            document.getElementById('cvv').value = '';
            document.getElementById('cardholderName').value = '';
            document.getElementById('setAsPrimary').checked = false;
        }

        // Show notification
        function showNotification(title, message, type = 'info') {
            const notification = document.getElementById('notification');
            const notificationTitle = document.getElementById('notificationTitle');
            const notificationMessage = document.getElementById('notificationMessage');
            
            // Set notification type
            notification.className = `notification ${type}`;
            
            // Set icon based on type
            let icon = 'fa-info-circle';
            if (type === 'success') icon = 'fa-check-circle';
            if (type === 'error') icon = 'fa-exclamation-circle';
            if (type === 'warning') icon = 'fa-exclamation-triangle';
            
            notification.querySelector('i').className = `fas ${icon}`;
            
            // Set content
            notificationTitle.textContent = title;
            notificationMessage.textContent = message;
            
            // Show notification
            notification.classList.add('show');
            
            // Auto hide after 5 seconds
            setTimeout(() => {
                notification.classList.remove('show');
            }, 5000);
        }

        // Close notification when clicked
        document.getElementById('notification').addEventListener('click', function() {
            this.classList.remove('show');
        });