// Chart instances
        let charts = {};
        
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize all charts
            initCharts();
            
            // Set current date
            const currentDate = new Date();
            const dateString = currentDate.toLocaleDateString('en-US', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });
            document.getElementById('currentDate').textContent = dateString;
            
            // Time period filter
            document.getElementById('timePeriod').addEventListener('change', function() {
                const days = parseInt(this.value);
                updateChartsData(days);
                showToast(`Showing data for last ${days} days`, 'info');
            });
        });
        
        function initCharts() {
            // Completion Trend Chart
            const completionCtx = document.getElementById('completionChart').getContext('2d');
            charts.completion = new Chart(completionCtx, {
                type: 'line',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
                    datasets: [{
                        label: 'Completed Tasks',
                        data: [45, 52, 48, 61, 55, 68, 72],
                        borderColor: '#4A6FA5',
                        backgroundColor: 'rgba(74, 111, 165, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4
                    }, {
                        label: 'Total Tasks',
                        data: [58, 65, 62, 75, 70, 82, 92],
                        borderColor: '#E74C3C',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Number of Tasks'
                            }
                        }
                    }
                }
            });
            
            // Status Distribution Chart
            const statusCtx = document.getElementById('statusChart').getContext('2d');
            charts.status = new Chart(statusCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Completed', 'In Progress', 'Pending', 'Hold'],
                    datasets: [{
                        data: [78, 15, 5, 2],
                        backgroundColor: [
                            '#2DA44E',
                            '#4A6FA5',
                            '#F39C12',
                            '#E74C3C'
                        ],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `${context.label}: ${context.raw}%`;
                                }
                            }
                        }
                    }
                }
            });
            
            // Create legend for status chart
            createLegend('statusLegend', [
                { label: 'Completed', color: '#2DA44E' },
                { label: 'In Progress', color: '#4A6FA5' },
                { label: 'Pending', color: '#F39C12' },
                { label: 'Hold', color: '#E74C3C' }
            ]);
            
            // Team Performance Chart
            const teamCtx = document.getElementById('teamChart').getContext('2d');
            charts.team = new Chart(teamCtx, {
                type: 'radar',
                data: {
                    labels: ['Completion', 'Speed', 'Quality', 'Communication', 'Availability'],
                    datasets: [
                        {
                            label: 'David Wilson',
                            data: [92, 88, 85, 90, 87],
                            backgroundColor: 'rgba(74, 111, 165, 0.2)',
                            borderColor: '#4A6FA5',
                            borderWidth: 2,
                            pointBackgroundColor: '#4A6FA5'
                        },
                        {
                            label: 'Emma Davis',
                            data: [88, 85, 92, 87, 90],
                            backgroundColor: 'rgba(46, 204, 113, 0.2)',
                            borderColor: '#2ecc71',
                            borderWidth: 2,
                            pointBackgroundColor: '#2ecc71'
                        },
                        {
                            label: 'Michael Brown',
                            data: [85, 90, 87, 85, 88],
                            backgroundColor: 'rgba(155, 89, 182, 0.2)',
                            borderColor: '#9b59b6',
                            borderWidth: 2,
                            pointBackgroundColor: '#9b59b6'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        r: {
                            angleLines: {
                                display: true
                            },
                            suggestedMin: 50,
                            suggestedMax: 100
                        }
                    }
                }
            });
            
            // Weekly Workload Chart
            const workloadCtx = document.getElementById('workloadChart').getContext('2d');
            charts.workload = new Chart(workloadCtx, {
                type: 'bar',
                data: {
                    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    datasets: [{
                        label: 'Tasks Assigned',
                        data: [12, 19, 15, 22, 18, 8, 5],
                        backgroundColor: '#4A6FA5',
                        borderColor: '#2E4C7D',
                        borderWidth: 1
                    }, {
                        label: 'Tasks Completed',
                        data: [10, 16, 13, 19, 15, 6, 4],
                        backgroundColor: '#2DA44E',
                        borderColor: '#1e8449',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Number of Tasks'
                            }
                        }
                    }
                }
            });
            
            // Revenue by Service Chart
            const revenueCtx = document.getElementById('revenueChart').getContext('2d');
            charts.revenue = new Chart(revenueCtx, {
                type: 'polarArea',
                data: {
                    labels: ['Website Design', 'Mobile Apps', 'SEO', 'Content', 'Branding'],
                    datasets: [{
                        data: [45000, 32000, 18000, 12000, 25000],
                        backgroundColor: [
                            '#4A6FA5',
                            '#2DA44E',
                            '#F39C12',
                            '#E74C3C',
                            '#9B59B6'
                        ],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
            
            // Create legend for revenue chart
            createLegend('revenueLegend', [
                { label: 'Website Design: $45,000', color: '#4A6FA5' },
                { label: 'Mobile Apps: $32,000', color: '#2DA44E' },
                { label: 'SEO: $18,000', color: '#F39C12' },
                { label: 'Content: $12,000', color: '#E74C3C' },
                { label: 'Branding: $25,000', color: '#9B59B6' }
            ]);
            
            // Department Time Analysis Chart
            const departmentCtx = document.getElementById('departmentChart').getContext('2d');
            charts.department = new Chart(departmentCtx, {
                type: 'bar',
                data: {
                    labels: ['Design', 'Development', 'Marketing', 'Content', 'QA'],
                    datasets: [
                        {
                            label: 'Avg. Completion Time (days)',
                            data: [2.5, 4.2, 3.1, 2.8, 3.5],
                            backgroundColor: '#4A6FA5',
                            borderColor: '#2E4C7D',
                            borderWidth: 1,
                            yAxisID: 'y'
                        },
                        {
                            label: 'Overdue Tasks',
                            data: [1, 5, 2, 1, 3],
                            backgroundColor: '#E74C3C',
                            borderColor: '#c0392b',
                            borderWidth: 1,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {
                                display: true,
                                text: 'Days'
                            }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: {
                                display: true,
                                text: 'Number of Tasks'
                            },
                            grid: {
                                drawOnChartArea: false
                            }
                        }
                    }
                }
            });
        }
        
        function createLegend(containerId, items) {
            const container = document.getElementById(containerId);
            container.innerHTML = '';
            
            items.forEach(item => {
                const legendItem = document.createElement('div');
                legendItem.className = 'legend-item';
                legendItem.innerHTML = `
                    <span class="legend-color" style="background-color: ${item.color}"></span>
                    <span class="legend-label">${item.label}</span>
                `;
                container.appendChild(legendItem);
            });
        }
        
        function changeChartType(chartName, type) {
            if (charts[chartName]) {
                charts[chartName].config.type = type;
                charts[chartName].update();
                
                // Update button states
                const buttons = document.querySelectorAll(`[onclick*="${chartName}"]`);
                buttons.forEach(btn => {
                    if (btn.textContent.toLowerCase() === type) {
                        btn.classList.add('active');
                    } else {
                        btn.classList.remove('active');
                    }
                });
            }
        }
        
        function updateChartsData(days) {
            // Simulate data update based on time period
            const factor = days / 30; // Normalize to 30 days
            
            // Update completion chart
            if (charts.completion) {
                const newData = charts.completion.data.datasets[0].data.map(value => 
                    Math.round(value * factor)
                );
                charts.completion.data.datasets[0].data = newData;
                charts.completion.update();
            }
            
            // Update workload chart
            if (charts.workload) {
                const newWorkloadData = charts.workload.data.datasets[0].data.map(value => 
                    Math.round(value * factor)
                );
                charts.workload.data.datasets[0].data = newWorkloadData;
                charts.workload.update();
            }
            
            showToast(`Charts updated for ${days} days period`, 'success');
        }
        
        function exportCharts() {
            // Create a temporary canvas to combine charts
            const exportCanvas = document.createElement('canvas');
            exportCanvas.width = 1600;
            exportCanvas.height = 2000;
            const ctx = exportCanvas.getContext('2d');
            
            // Set background
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);
            
            // Add title
            ctx.fillStyle = '#2E4C7D';
            ctx.font = 'bold 24px Arial';
            ctx.fillText('Manager Dashboard - Graph Reports', 50, 50);
            
            ctx.font = '14px Arial';
            ctx.fillStyle = '#666';
            ctx.fillText(`Generated on: ${new Date().toLocaleDateString()}`, 50, 80);
            
            // In a real application, you would render all charts to this canvas
            // For now, we'll just show a toast
            showToast('Exporting charts as PDF...', 'info');
            
            // Simulate download
            setTimeout(() => {
                showToast('Report exported successfully!', 'success');
            }, 1500);
        }
        
        function showToast(message, type = 'success') {
            const toast = document.getElementById('toast');
            const toastMessage = document.getElementById('toastMessage');
            
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
        
        // Refresh charts every 5 minutes (simulate real-time updates)
        setInterval(() => {
            // Update a random chart with new data
            const chartNames = Object.keys(charts);
            const randomChart = chartNames[Math.floor(Math.random() * chartNames.length)];
            
            if (charts[randomChart] && Math.random() > 0.7) { // 30% chance to update
                const datasetIndex = Math.floor(Math.random() * charts[randomChart].data.datasets.length);
                const dataIndex = Math.floor(Math.random() * charts[randomChart].data.datasets[datasetIndex].data.length);
                
                // Add small random variation
                const currentValue = charts[randomChart].data.datasets[datasetIndex].data[dataIndex];
                const variation = Math.random() > 0.5 ? 1 : -1;
                const newValue = Math.max(0, currentValue + variation * Math.random() * 5);
                
                charts[randomChart].data.datasets[datasetIndex].data[dataIndex] = Math.round(newValue);
                charts[randomChart].update();
            }
        }, 300000); // 5 minutes
