from flask import Blueprint, request, jsonify, session, redirect, url_for
from flask_mail import Message
from flask_dance.contrib.google import make_google_blueprint, google
from itsdangerous import URLSafeTimedSerializer
from extensions import bcrypt, mail, client
from config import Config
from flask import current_app
import random
from datetime import datetime, timedelta

from datetime import timedelta
import os


auth = Blueprint('auth', __name__)
s = URLSafeTimedSerializer(Config.SECRET_KEY)
users = client['test'].users


# Google OAuth
google_bp = make_google_blueprint(
    client_id=Config.GOOGLE_CLIENT_ID,
    client_secret=Config.GOOGLE_CLIENT_SECRET,
    redirect_url="/login/google/callback",
    scope=[
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid"
    ]
)

from oauthlib.oauth2.rfc6749.errors import TokenExpiredError

@auth.route("/login/google/callback")
def google_callback():
    print(f"Google authorized? {google.authorized}")

    if not google.authorized:
        return jsonify({'error': 'Google authorization failed'}), 403

    try:
        resp = google.get("/oauth2/v2/userinfo")
        if not resp.ok:
            return jsonify({'error': 'Failed to fetch user info'}), 400

        user_info = resp.json()
        email = user_info["email"]
        user = users.find_one({'email': email})

        if not user:
            users.insert_one({
                'email': email,
                'username': user_info.get('name', ''),
                'email_verified': True,
                'login_via': 'google'
            })
            user = users.find_one({'email': email})

        session.permanent = True
        session['user_id'] = str(user['_id'])
        session['username'] = user.get('username', '')

        return redirect(url_for('home'))
    except TokenExpiredError:
        # Force re-login if token expired
        return redirect(url_for("google.login"))
    except Exception as e:
        return jsonify({'error': 'Something went wrong', 'message': str(e)}), 500
@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email, password = data.get('email'), data.get('password')
    user = users.find_one({'email': email})

    if not user:
        return jsonify({'error': 'Email not found'}), 404
    if not user.get('email_verified', False):
        return jsonify({'error': 'Email not verified'}), 403
    if not bcrypt.check_password_hash(user['password'], password):
        return jsonify({'error': 'Incorrect password'}), 401

    session.permanent = True
    session['user_id'] = str(user['_id'])
    session['username'] = user.get('username', '')
    return jsonify({'message': 'Login successful'}), 200

@auth.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    confirm = data.get('confirm_password')

    if users.find_one({'email': email}):
        return jsonify({'error': 'Email already exists'}), 400
    if password != confirm:
        return jsonify({'error': 'Passwords do not match'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    users.insert_one({'username': username, 'email': email, 'password': hashed_password, 'email_verified': False})

    # Generate token and verification URL
    token = s.dumps(email, salt='email-confirm')
    verify_url = url_for('auth.serve_verification_page', token=token, _external=True)

    # Send email
    msg = Message("Verify your email", sender=current_app.config['MAIL_USERNAME'], recipients=[email])
    msg.body = f"Hi {username}, click to verify:\n{verify_url}\nLink expires in 1 hour."

    try:
        mail.send(msg)
    except Exception as e:
        return jsonify({'error': 'Failed to send email', 'message': str(e)}), 500

    # ✅ This will allow your frontend to redirect to preview-verification
    return jsonify({
        'message': 'Signup successful, check your email to verify.',
        'email': email,
        'token': token
    }), 201


@auth.route('/verify-email', methods=['GET'])
def verify_email():
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'Missing token'}), 400

    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
    except Exception as e:
        return jsonify({'error': 'Verification link invalid or expired'}), 400

    user = users.find_one({'email': email})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.get('email_verified'):
        return jsonify({'message': 'Email already verified.'}), 200

    users.update_one({'email': email}, {'$set': {'email_verified': True}})
    return jsonify({'message': 'Email verified successfully!'}), 200

@auth.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'}), 200


@auth.route('/me', methods=['GET'])
def get_current_user():
    if 'user_id' in session:
        return jsonify({'userId': session['user_id'], 'username': session.get('username', '')}), 200
    return jsonify({'error': 'Not logged in'}), 401

from flask import render_template

@auth.route('/verify-page')
def serve_verification_page():
    token = request.args.get('token')
    if not token:
        return render_template('verify.html', message="Missing token", status="error")

    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
    except Exception:
        return render_template('verify.html', message="Invalid or expired token", status="error")

    user = users.find_one({'email': email})
    if not user:
        return render_template('verify.html', message="User not found", status="error")

    if not user.get('email_verified'):
        users.update_one({'email': email}, {'$set': {'email_verified': True}})
        return render_template('verify.html', message="Email verified successfully!", status="success")

    return render_template('verify.html', message="Email already verified.", status="info")

@auth.route('/preview-verification')
def preview_verification():
    email = request.args.get('email')
    token = request.args.get('token')

    if not email or not token:
        return "Missing email or token", 400

    verify_link = url_for('auth.serve_verification_page', token=token, _external=True)
    return render_template('verify_email_template.html', email=email, verify_link=verify_link)

from flask import request, jsonify

@auth.route('/resend-email', methods=['POST'])
def resend_email():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'message': 'Email is required.'}), 400

    user = users.find_one({'email': email})
    if not user:
        return jsonify({'message': 'User not found.'}), 404

    if user.get('email_verified'):
        return jsonify({'message': 'Email already verified.'}), 200

    # Recreate verification email
    token = s.dumps(email, salt='email-confirm')
    verify_url = url_for('auth.serve_verification_page', token=token, _external=True)

    msg = Message("Verify your email", sender=current_app.config['MAIL_USERNAME'], recipients=[email])
    msg.body = f"Hi {user['username']}, click to verify:\n{verify_url}\nLink expires in 1 hour."

    try:
        mail.send(msg)
    except Exception as e:
        return jsonify({'message': 'Failed to resend email', 'error': str(e)}), 500

    return jsonify({'message': 'Verification email resent successfully.'}), 200



@auth.route('/request-otp', methods=['POST'])
def request_otp():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    user = users.find_one({'email': email})
    if not user:
        return jsonify({'error': 'Email not registered'}), 404

    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    expiry_time = datetime.utcnow() + timedelta(minutes=5)

    # Store OTP and expiry in user document
    users.update_one(
        {'email': email},
        {'$set': {'reset_otp': otp, 'otp_expiry': expiry_time}}
    )

    # Send email
    msg = Message("Your OTP for Password Reset", sender=current_app.config['MAIL_USERNAME'], recipients=[email])
    msg.body = f"Hi {user.get('username', '')},\n\nYour OTP is: {otp}\nIt will expire in 5 minutes."

    try:
        mail.send(msg)
    except Exception as e:
        return jsonify({'error': 'Failed to send OTP email', 'message': str(e)}), 500

    return jsonify({'message': 'OTP sent to your email.'}), 200


@auth.route('/reset-password', methods=['POST'])
def reset_password_with_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not all([email, otp, new_password, confirm_password]):
        return jsonify({'error': 'All fields are required'}), 400

    if new_password != confirm_password:
        return jsonify({'error': 'Passwords do not match'}), 400

    user = users.find_one({'email': email})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Check if OTP is correct and not expired
    if user.get('reset_otp') != otp:
        return jsonify({'error': 'Invalid OTP'}), 400

    if datetime.utcnow() > user.get('otp_expiry', datetime.utcnow()):
        return jsonify({'error': 'OTP has expired'}), 400

    # Reset password
    hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    users.update_one(
        {'email': email},
        {'$set': {'password': hashed_password},
         '$unset': {'reset_otp': "", 'otp_expiry': ""}}  # Remove OTP fields
    )

    return jsonify({'message': 'Password reset successful'}), 200
