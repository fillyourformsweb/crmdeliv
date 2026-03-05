@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    
    if user and user.check_password(password):
        if not user.is_active:
            return jsonify({'error': 'Account is disabled'}), 401
            
        access_token = create_access_token(identity=user.id)
        return jsonify({
            'success': True,
            'token': access_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
        })
    
    return jsonify({'error': 'Invalid username or password'}), 401


@app.route('/api/auth/request-otp', methods=['POST'])
def api_request_otp():
    data = request.get_json()
    email = data.get('email')
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Email not found'}), 404
        
    # Generate 6-digit OTP
    otp = secrets.token_hex(3).upper() # Generates 6 char hex
    user.otp_code = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()
    
    # In a real app, send email here. For now, we return it for testing/demo.
    # verify_email(user.email, otp) 
    
    return jsonify({
        'success': True, 
        'message': 'OTP sent to email',
        'debug_otp': otp # REMOVE IN PRODUCTION
    })


@app.route('/api/auth/reset-password', methods=['POST'])
def api_reset_password():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    new_password = data.get('new_password')
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    if not user.otp_code or user.otp_code != otp:
        return jsonify({'error': 'Invalid OTP'}), 400
        
    if user.otp_expiry < datetime.utcnow():
        return jsonify({'error': 'OTP expired'}), 400
        
    user.set_password(new_password)
    user.otp_code = None
    user.otp_expiry = None
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Password updated successfully'})
