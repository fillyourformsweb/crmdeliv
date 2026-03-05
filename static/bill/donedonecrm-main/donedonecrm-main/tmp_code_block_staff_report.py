@app.route('/api/reports/staff-performance', methods=['GET'])
@login_required
@role_required(['admin', 'manager', 'staff'])
def get_staff_performance_detailed_report():
    """Get detailed staff performance report for Admin Report > Staff Performance tab"""
    try:
        user = User.query.get(session['user_id'])
        
        # Get parameters
        staff_id = request.args.get('staff_id')
        branch_id = request.args.get('branch_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Base query
        query = Task.query
        
        # Date filter
        if date_from:
            try:
                start_dt = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(Task.created_at >= start_dt)
            except ValueError:
                pass
        
        if date_to:
            try:
                end_dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(Task.created_at < end_dt)
            except ValueError:
                pass
                
        # Role-based scoping
        if user.post.lower() == 'staff':
            # Staff can only see their own tasks
            query = query.filter(Task.assigned_to_id == user.id)
        elif user.post.lower() == 'manager':
            # Manager sees branch tasks, or specific staff if selected
            if user.branch_id:
                query = query.filter(Task.branch_id == user.branch_id)
            if staff_id and staff_id != 'all':
                query = query.filter(Task.assigned_to_id == int(staff_id))
        elif user.post.lower() == 'admin':
            if branch_id and branch_id != 'all':
                query = query.filter(Task.branch_id == int(branch_id))
            if staff_id and staff_id != 'all':
                query = query.filter(Task.assigned_to_id == int(staff_id))
                
        tasks = query.order_by(Task.created_at.desc()).all()
        
        # --- Metrics Calculation ---
        total_tasks = len(tasks)
        completed_tasks = [t for t in tasks if t.status == 'completed']
        pending_tasks = [t for t in tasks if t.status == 'pending']
        in_progress_tasks = [t for t in tasks if t.status == 'in_progress']
        cancelled_tasks = [t for t in tasks if t.status == 'cancelled']
        
        completion_rate = (len(completed_tasks) / total_tasks * 100) if total_tasks > 0 else 0
        total_revenue = sum(float(t.paid_amount or 0) for t in tasks)
        
        # Avg completion time (simple approximation)
        total_hours = 0
        count_with_time = 0
        for t in completed_tasks:
            if t.created_at and t.completed_at:
                diff = (t.completed_at - t.created_at).total_seconds() / 3600
                total_hours += diff
                count_with_time += 1
        avg_time = (total_hours / count_with_time) if count_with_time > 0 else 0
        
        # Tasks per day (approximate based on date range or 30 days)
        days_span = 30
        if date_from and date_to:
            try:
                d1 = datetime.strptime(date_from, '%Y-%m-%d')
                d2 = datetime.strptime(date_to, '%Y-%m-%d')
                days_span = max(1, (d2 - d1).days + 1)
            except:
                pass
        avg_tasks_per_day = total_tasks / days_span
        avg_revenue = total_revenue / days_span
        
        metrics = {
            'avg_completion_time': round(avg_time, 1),
            'completion_rate': round(completion_rate, 1),
            'avg_tasks_per_day': round(avg_tasks_per_day, 1),
            'avg_revenue': round(avg_revenue, 2)
        }
        
        # --- Trend Data (Last 7 days or range) ---
        trend_dates = []
        trend_completed = []
        trend_pending = []
        
        # Iterate last 7 days from today (or based on query)
        base_date = datetime.now()
        for i in range(6, -1, -1):
            d = base_date - timedelta(days=i)
            d_str = d.strftime('%Y-%m-%d')
            display_date = d.strftime('%d %b')
            
            # Simple count for that day in result set
            day_tasks = [t for t in tasks if t.created_at and t.created_at.strftime('%Y-%m-%d') == d_str]
            c_count = len([t for t in day_tasks if t.status == 'completed'])
            p_count = len([t for t in day_tasks if t.status == 'pending'])
            
            trend_dates.append(display_date)
            trend_completed.append(c_count)
            trend_pending.append(p_count)
            
        trend_data = {
            'dates': trend_dates,
            'completed': trend_completed,
            'pending': trend_pending
        }
        
        # --- Breakdown ---
        breakdown = [
            {'status': 'completed', 'count': len(completed_tasks), 'percentage': (len(completed_tasks)/total_tasks*100) if total_tasks else 0},
            {'status': 'pending', 'count': len(pending_tasks), 'percentage': (len(pending_tasks)/total_tasks*100) if total_tasks else 0},
            {'status': 'in_progress', 'count': len(in_progress_tasks), 'percentage': (len(in_progress_tasks)/total_tasks*100) if total_tasks else 0},
            {'status': 'cancelled', 'count': len(cancelled_tasks), 'percentage': (len(cancelled_tasks)/total_tasks*100) if total_tasks else 0}
        ]
        
        # --- Task Details (Top 100 for table) ---
        task_details = []
        for t in tasks[:100]:
            task_details.append({
                'id': t.id,
                'order_no': t.order_no or t.id,
                'task_name': t.service_name or 'N/A', # Fallback for old code
                'service_name': t.service_name or 'N/A',
                'customer_name': t.customer_name or 'Walk-in',
                'service_type': 'Normal' if not getattr(t, 'service_type', None) else t.service_type, # adjust if service_type is on Task or related Service
                'assigned_date': t.created_at.isoformat() if t.created_at else None,
                'completed_date': t.completed_at.isoformat() if t.completed_at else None,
                'status': t.status,
                'rating': 0, # Placeholder
                'revenue': float(t.paid_amount or 0)
            })
            
        return jsonify({
            'success': True,
            'metrics': metrics,
            'trend_data': trend_data,
            'breakdown': breakdown,
            'task_details': task_details,
            'today_data': [len(completed_tasks), len(pending_tasks), len(in_progress_tasks), len(cancelled_tasks)] # Simplified for pie chart
        })
        
    except Exception as e:
        print(f"Error in detailed staff performance report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
