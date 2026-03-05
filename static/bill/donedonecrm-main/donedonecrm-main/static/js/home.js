
        // Simulated Database
        const database = {
            user: {
                isLoggedIn: false,
                name: "John Doe",
                email: "john@example.com",
                avatar: "JD"
            },
            notifications: [
                {
                    id: 1,
                    title: "UPSC Civil Services Exam 2024",
                    description: "Notification for UPSC Civil Services Preliminary Examination has been released. Last date to apply: 20th March 2024.",
                    date: "15 Feb 2024",
                    category: "Exam",
                    isNew: true
                },
                {
                    id: 2,
                    title: "SSC CGL 2024 Notification",
                    description: "SSC Combined Graduate Level Exam 2024 notification released. Application window opens from 10th April 2024.",
                    date: "10 Feb 2024",
                    category: "Job",
                    isNew: false
                },
                {
                    id: 3,
                    title: "Scholarship Application Deadline",
                    description: "National Scholarship Portal applications close on 28th February 2024. Apply now for various scholarships.",
                    date: "8 Feb 2024",
                    category: "Student",
                    isNew: false
                }
            ]
        };

        // DOM Elements
        const loginBtn = document.getElementById('loginBtn');
        
        const userAvatar = document.getElementById('userAvatar');
        const notificationBell = document.getElementById('notificationBell');
        const notificationList = document.getElementById('notificationList');

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            updateNotificationCount();
            renderNotifications();
            setupEventListeners();
        });

       
            
        
            
            

 

        // Notifications
        function updateNotificationCount() {
            const newCount = database.notifications.filter(n => n.isNew).length;
            const countElement = notificationBell.querySelector('.notification-count');
            countElement.textContent = newCount;
        }

        function renderNotifications() {
            notificationList.innerHTML = '';
            
            database.notifications.forEach(notification => {
                const item = document.createElement('div');
                item.className = `notification-item ${notification.isNew ? 'new' : ''}`;
                item.innerHTML = `
                    <div class="notification-icon">
                        <i class="fas fa-${getNotificationIcon(notification.category)}"></i>
                    </div>
                    <div class="notification-content">
                        <div class="notification-title">${notification.title}</div>
                        <div class="notification-desc">${notification.description}</div>
                        <div class="notification-meta">
                            <span class="notification-date">Posted: ${notification.date}</span>
                            <span class="notification-category">${notification.category}</span>
                        </div>
                    </div>
                `;
                
                item.addEventListener('click', () => {
                    notification.isNew = false;
                    updateNotificationCount();
                    renderNotifications();
                });
                
                notificationList.appendChild(item);
            });
        }

        function getNotificationIcon(category) {
            const icons = {
                'Exam': 'file-alt',
                'Job': 'bullhorn',
                'Student': 'graduation-cap',
                'Business': 'briefcase',
                'Scheme': 'hand-holding-heart'
            };
            return icons[category] || 'bell';
        }

        // Check if user is logged in from localStorage
        const savedUser = localStorage.getItem('user');
        if (savedUser) {
            const user = JSON.parse(savedUser);
            database.user = user;
            if (user.isLoggedIn) {
                loginBtn.innerHTML = '<i class="fas fa-sign-out-alt"></i> Logout';
                userAvatar.innerHTML = user.avatar;
                userAvatar.style.background = 'linear-gradient(135deg, var(--secondary), var(--secondary-dark))';
            }
        }
    