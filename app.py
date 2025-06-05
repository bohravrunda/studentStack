from dotenv import load_dotenv
import os
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from pymongo import MongoClient
from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from werkzeug.utils import secure_filename
from bson import ObjectId
from datetime import datetime
from flask import render_template



load_dotenv()

app = Flask(__name__)



# Flask Configurations (after app creation)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'this_should_be_secret')
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

mail = Mail(app)
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
bcrypt = Bcrypt(app)
CORS(app, supports_credentials=True, origins="*")

MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client['flask_auth']

users = db.users
services = db.services

UPLOAD_FOLDER = 'uploads/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Signup Route
@app.route('/signup', methods=['POST'])
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

    users.insert_one({
        'username': username,
        'email': email,
        'password': hashed_password,
        'email_verified': False
    })

    token = s.dumps(email, salt='email-confirm')
    verify_url = f"http://localhost:5500/verify.html?token={token}"  # Update frontend URL if needed

    msg = Message(subject="Verify your email",
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[email])
    msg.body = f"Hi {username},\nClick to verify your email:\n{verify_url}\nThis link expires in 1 hour."

    try:
        mail.send(msg)
        print("Verification email sent to:", email)

    except Exception as e:
        print("Mail send error:", e)
        print("Mail send error:", e)

        return jsonify({'error': 'Failed to send verification email'}), 500

    return jsonify({'message': 'Signup successful, check your email to verify.'}), 201

@app.route('/verify-page')
def verify_page():
    return render_template('verify.html')


@app.route('/verify-email', methods=['GET'])
def verify_email():
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'Missing token'}), 400

    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
    except Exception as e:
        print("Verification error:", e)
        return jsonify({'error': 'Verification link invalid or expired.'}), 400

    user = users.find_one({'email': email})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.get('email_verified'):
        return jsonify({'message': 'Email already verified.'}), 200

    users.update_one({'email': email}, {'$set': {'email_verified': True}})
    return jsonify({'message': 'Email verified successfully!'}), 200



@app.route('/get-all-services', methods=['GET'])
def get_all_services():
    try:
        services_cursor = services.find()
        services_list = []
        for service in services_cursor:
            service['_id'] = str(service['_id'])  # Convert ObjectId to string
            service['user_id'] = str(service['user_id'])  # Optional: convert user_id too
            services_list.append(service)

        return jsonify(services_list), 200

    except Exception as e:
        print("Error in /get-all-services:", str(e))
        return jsonify({'error': 'Failed to fetch all services', 'message': str(e)}), 500

# Login Route
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = users.find_one({'email': email})
    if not user:
        return jsonify({'error': 'Email not found'}), 404

    if not user.get('email_verified', False):
        return jsonify({'error': 'Email not verified'}), 403

    if not bcrypt.check_password_hash(user['password'], password):
        return jsonify({'error': 'Incorrect password'}), 401

    return jsonify({
        'message': 'Login successful',
        'userId': str(user['_id']),          # Convert ObjectId to string
        'username': user.get('username', '') # Optional: return empty string if not found
    }), 200


@app.route('/get-services-by-userid', methods=['GET'])
def get_services_by_userid():
    try:
        user_id = request.args.get('userId')  # Get userId from query parameter

        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400

        services_cursor = services.find({'user_id': user_id})
        services_list = []
        for service in services_cursor:
            service['_id'] = str(service['_id'])  # Convert ObjectId to string
            services_list.append(service)

        return jsonify(services_list), 200

    except Exception as e:
        print("Error in /get-services-by-userid:", str(e))
        return jsonify({'error': 'Failed to fetch services', 'message': str(e)}), 500



@app.route('/create-service', methods=['POST'])
def create_service():
    try:
        form = request.form
        files = request.files.getlist('proof[]')

        # Extract form fields
        user_id = form.get('userId')
        username = form.get('username')
        service_name = form.get('service_name')
        category = form.get('category')
        provider_name = form.get('provider_name')
        provider_email = form.get('provider_email')
        provider_location = form.get('provider_location')
        starting_date = form.get('starting_date')
        ending_date = form.get('ending_date')
        price = form.get('price')
        payment_method = form.get('payment_method')
        level = form.get('level')
        additional_note = form.get('additional_note')

        # Handle multiple values
        available_days = form.getlist('available_days[]')
        languages = form.getlist('language[]')

        # Save uploaded files
        file_paths = []
        for file in files:
            if file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                file_paths.append(filepath)

        # Prepare the service document
        service_doc = {
            'user_id': user_id,
            'username': username,
            'service_name': service_name,
            'category': category,
            'provider': {
                'name': provider_name,
                'email': provider_email,
                'location': provider_location
            },
            'availability': {
                'from': starting_date,
                'to': ending_date,
                'days': available_days
            },
            'cost': {
                'price': price,
                'payment_method': payment_method
            },
            'level': level,
            'language': languages,
            'portfolio_files': file_paths,
            'additional_note': additional_note,
            'created_at': datetime.utcnow()
        }

        services.insert_one(service_doc)

        return jsonify({'message': 'Service created successfully'}), 201

    except Exception as e:
        print("Error in /create-service:", str(e))
        return jsonify({'error': 'Service creation failed', 'message': str(e)}), 500
    
    


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

