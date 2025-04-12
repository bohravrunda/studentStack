from flask import Flask, request, jsonify, session
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)

# ✅ Enable CORS with credentials
CORS(app, supports_credentials=True)

# Session configuration
app.secret_key = os.getenv('SECRET_KEY') or 'your_secret_key'  # Fallback in case .env is missing
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

# Connect to MongoDB Atlas
mongo_uri = os.getenv("MONGO_URI") or "your_mongo_uri"
client = MongoClient(mongo_uri)
db = client["test"]
users_collection = db["users"]

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

        users_collection.insert_one({
            "email": email,
            "username": username,
            "password": hashed_pw
        })

        return jsonify({"message": "User registered successfully"}), 201

    except Exception as e:
        print("Signup error:", e)
        return jsonify({"message": "An error occurred. Please try again."}), 500

# Login route
@app.route('/login', methods=['POST'])
def login():
    try:
        print("Login route hit!")  # ✅ Confirm if this runs
        data = request.json
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"message": "Email and password are required"}), 400

        user = users_collection.find_one({"email": email})
        if not user:
            return jsonify({"message": "User not found"}), 404

        if bcrypt.check_password_hash(user["password"], password):
            session["user_id"] = str(user["_id"])
            return jsonify({"message": "Login successful", "session_id": "session_created"}), 200
        else:
            return jsonify({"message": "Incorrect password"}), 401

    except Exception as e:
        print("Login error:", e)
        return jsonify({"message": "Something went wrong"}), 500

@app.route('/logout', methods=['POST'])
def logout():
    session.pop("user_id", None)
    return jsonify({"message": "Logout successful"}), 200

if __name__ == '__main__':
    app.run(debug=True)
