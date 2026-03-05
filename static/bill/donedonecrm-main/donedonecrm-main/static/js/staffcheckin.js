// Staff Check-in/out functionality
document.addEventListener('DOMContentLoaded', function() {
    loadTodayStatus();
    updateCurrentTime();
    
    // Update time every second
    setInterval(updateCurrentTime, 1000);
});

async function loadTodayStatus() {
    try {
        const response = await fetch('/api/attendance/today');
        const status = await response.json();
        
        const statusDiv = document.getElementById('currentStatus');
        const checkinBtn = document.getElementById('checkinBtn');
        const checkoutBtn = document.getElementById('checkoutBtn');
        
        if (status && status.check_in) {
            const checkInTime = new Date(status.check_in).toLocaleTimeString();
            
            if (status.check_out) {
                const checkOutTime = new Date(status.check_out).toLocaleTimeString();
                statusDiv.innerHTML = `
                    <p><i class="fas fa-check-circle" style="color: #28a745;"></i> 
                    Checked In: ${checkInTime}</p>
                    <p><i class="fas fa-check-circle" style="color: #28a745;"></i> 
                    Checked Out: ${checkOutTime}</p>
                    <p><strong>Status:</strong> Completed for today</p>
                `;
                checkinBtn.disabled = true;
                checkoutBtn.disabled = true;
            } else {
                statusDiv.innerHTML = `
                    <p><i class="fas fa-check-circle" style="color: #28a745;"></i> 
                    Checked In: ${checkInTime}</p>
                    <p><i class="fas fa-clock" style="color: #ffc107;"></i> 
                    Currently working...</p>
                `;
                checkinBtn.disabled = true;
                checkoutBtn.disabled = false;
            }
        } else {
            statusDiv.innerHTML = `
                <p><i class="fas fa-clock" style="color: #6c757d;"></i> 
                Not checked in yet</p>
                <p>Please check in when you start work</p>
            `;
            checkinBtn.disabled = false;
            checkoutBtn.disabled = true;
        }
        
        // Load attendance history
        loadAttendanceHistory();
    } catch (error) {
        console.error('Error loading status:', error);
        document.getElementById('currentStatus').innerHTML = 
            '<p style="color: #dc3545;">Error loading status</p>';
    }
}

async function checkIn() {
    const branchSelect = document.getElementById('branchSelect');
    const branch = branchSelect.value;
    
    if (!branch) {
        showMessage('Please select a branch', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/attendance/checkin', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({branch: branch})
        });
        
        const result = await response.json();
        showMessage(result.message, result.success ? 'success' : 'error');
        
        if (result.success) {
            loadTodayStatus();
        }
    } catch (error) {
        console.error('Error checking in:', error);
        showMessage('Error checking in', 'error');
    }
}

async function checkOut() {
    try {
        const response = await fetch('/api/attendance/checkout', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        const result = await response.json();
        showMessage(result.message, result.success ? 'success' : 'error');
        
        if (result.success) {
            loadTodayStatus();
        }
    } catch (error) {
        console.error('Error checking out:', error);
        showMessage('Error checking out', 'error');
    }
}

async function loadAttendanceHistory() {
    try {
        // This would need a backend endpoint for attendance history
        // For now, just show recent status
        const response = await fetch('/api/attendance/today');
        const today = await response.json();
        
        const historyDiv = document.getElementById('attendanceHistory');
        
        if (today) {
            const date = new Date(today.check_in).toLocaleDateString();
            const checkIn = new Date(today.check_in).toLocaleTimeString();
            const checkOut = today.check_out ? 
                new Date(today.check_out).toLocaleTimeString() : 'Still working';
            
            historyDiv.innerHTML = `
                <div class="history-item">
                    <strong>${date}</strong>
                    <div>Check In: ${checkIn}</div>
                    <div>Check Out: ${checkOut}</div>
                    <div>Branch: ${today.branch}</div>
                </div>
            `;
        } else {
            historyDiv.innerHTML = '<p>No attendance records found</p>';
        }
    } catch (error) {
        console.error('Error loading history:', error);
        document.getElementById('attendanceHistory').innerHTML = 
            '<p style="color: #dc3545;">Error loading history</p>';
    }
}

function updateCurrentTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    const dateString = now.toLocaleDateString('en-IN', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    document.getElementById('currentTime').innerHTML = `
        <p><strong>${dateString}</strong></p>
        <p><i class="fas fa-clock"></i> ${timeString}</p>
    `;
}

function showMessage(message, type = 'info') {
    const messageDiv = document.getElementById('attendanceMessage');
    messageDiv.textContent = message;
    messageDiv.className = `message message-${type}`;
    messageDiv.style.display = 'block';
    
    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 3000);
}

function logout() {
    fetch('/logout')
        .then(() => {
            window.location.href = '/login';
        })
        .catch(error => {
            console.error('Logout error:', error);
        });
}