from flask import Flask, request, jsonify, session
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from flask_session import Session

import os
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)

# Secret key for sessions
app.secret_key = os.getenv('SECRET_KEY') or 'your_secret_key'

# Enable CORS with credentials
CORS(app, supports_credentials=True)

# Upload folder setup
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Session configuration
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"


# Connect to MongoDB
mongo_uri = os.getenv("MONGO_URI") or "your_mongo_uri"
client = MongoClient(mongo_uri)
db = client["test"]
users_collection = db["users"]

# Function to generate next small user_id
def get_next_user_id():
    last_user = users_collection.find_one(sort=[("user_id", -1)])
    return (last_user["user_id"] + 1) if last_user and "user_id" in last_user else 1

# Signup route
@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        email = data.get("email")
        password = data.get("password")
        confirm_password = data.get("confirm_password")
        username = data.get("username")

        if not email or not password or not confirm_password or not username:
            return jsonify({"message": "All fields are required"}), 400

        if password != confirm_password:
            return jsonify({"message": "Passwords do not match"}), 400

        if users_collection.find_one({"email": email}):
            return jsonify({"message": "User already exists"}), 409

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user_id = get_next_user_id()

        users_collection.insert_one({
            "user_id": user_id,
            "email": email,
            "username": username,
            "password": hashed_pw
        })

        return jsonify({
            "message": "User registered successfully",
            "username": username,
            "user_id": user_id
        }), 201

    except Exception as e:
        print("Signup error:", e)
        return jsonify({"message": "An error occurred. Please try again."}), 500

# Login route
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"message": "Email and password are required"}), 400

        user = users_collection.find_one({"email": email})
        if not user:
            return jsonify({"message": "User not found"}), 404

        if bcrypt.check_password_hash(user["password"], password):
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["email"] = user["email"]
            session["session_id"] = str(uuid.uuid4())

            return jsonify({
                "message": "Login successful",
                "username": user["username"],
                "user_id": user["user_id"]
            }), 200
        else:
            return jsonify({"message": "Incorrect password"}), 401

    except Exception as e:
        print("Login error:", e)
        return jsonify({"message": "Something went wrong"}), 500

# Get user session data
@app.route('/get_user', methods=['GET'])
def get_user():
    if "user_id" not in session or "username" not in session:
        return jsonify({"message": "Not logged in"}), 401
    return jsonify({
        "user_id": session["user_id"],
        "username": session["username"],
        "email": session.get("email"),
        "session_id": session.get("session_id")
    }), 200

# Logout route
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logout successful"}), 200

# Create Service route
@app.route('/create-service', methods=['POST'])
def create_service():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"message": "User not logged in"}), 401

        data = request.form.to_dict()
        data['language'] = request.form.getlist('language[]')
        data['available_days'] = request.form.getlist('available_days[]')

        uploaded_files = request.files.getlist('proof')
        proof_docs = []

        for file in uploaded_files:
            if file.filename == "":
                continue
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            proof_docs.append({
                "filename": filename,
                "file_url": filepath
            })

        service_doc = {
            "user_id": user_id,  # 🆕 Add user_id here
            "username": data.get("username"),
            "service_name": data.get("service_name"),
            "category": data.get("category"),
            "provider_info": {
                "name": data.get("provider_name"),
                "email": data.get("provider_email"),
                "location": data.get("provider_location")
            },
            "availability": {
                "starting_date": data.get("starting_date"),
                "ending_date": data.get("ending_date"),
                "available_days": data.get("available_days")
            },
            "cost": {
                "price": float(data.get("price", 0)),
                "payment_method": data.get("payment_method")
            },
            "level": data.get("level"),
            "language": data.get("language"),
            "proof": proof_docs,
            "additional_note": data.get("additional_note")
        }

        db.service.insert_one(service_doc)
        return jsonify({"message": "Service created successfully"}), 201

    except Exception as e:
        print("Error:", e)
        return jsonify({"message": "Something went wrong"}), 500

# Get Services
@app.route('/get-services', methods=['GET'])
def get_services():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"message": "User not logged in"}), 401

        services = list(db.service.find({"user_id": user_id}))
        if not services:
            return jsonify({"message": "No services found"}), 404

        for service in services:
            service['_id'] = str(service['_id'])

        return jsonify(services), 200

    except Exception as e:
        print("Error fetching services:", e)
        return jsonify({"message": "Something went wrong"}), 500

if __name__ == '__main__':
    app.run(debug=True)
