from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, current_app
from extensions import client
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
import os

profile = Blueprint('profile', __name__)
profile_collection = client['test'].profile  # Change 'test' to your DB name if needed

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------ PROFILE PICTURE UPLOAD ------------------
@profile.route('/upload-profile-pic', methods=['POST'])
def upload_profile_pic():
    if 'profile_pic' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['profile_pic']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file.save(filepath)

        file_url = f'/static/uploads/{filename}'  # Public URL path
        return jsonify({'profilePicUrl': file_url}), 200
    else:
        return jsonify({'error': 'Invalid file type'}), 400

# ------------------ SAVE PROFILE (CREATE) ------------------
@profile.route('/save-profile', methods=['POST'])
def save_profile():
    data = request.get_json()
    email = data.get("email")

    if profile_collection.find_one({"email": email}):
        return jsonify({"error": "Profile already exists."}), 409

    result = profile_collection.insert_one(data)
    return jsonify({"message": "Profile created successfully!", "id": str(result.inserted_id)}), 201

# ------------------ EDIT PROFILE (UPDATE) ------------------
@profile.route('/edit-profile', methods=['PUT'])
def edit_profile():
    data = request.get_json()
    email = data.get("email")

    if not profile_collection.find_one({"email": email}):
        return jsonify({"error": "Profile not found."}), 404

    profile_collection.update_one({"email": email}, {"$set": data})
    return jsonify({"message": "Profile updated successfully!"}), 200

# ------------------ GET PROFILE (READ) ------------------
@profile.route('/get-profile', methods=['GET'])
def get_profile():
    email = request.args.get("userId")

    profile_data = profile_collection.find_one({"email": email}, {"_id": 0})
    if not profile_data:
        return jsonify({"error": "Profile not found."}), 404

    return jsonify(profile_data), 200

# ------------------ RENDER PROFILE PAGE ------------------
@profile.route('/profile')
def profile_page():
    email = session.get('email')
    username = session.get('username', 'Guest')
    print("Session email:", email)  # DEBUG
    print("Session username:", username)

    if not email:
        return redirect(url_for('auth.login'))  # Optional: force login

    return render_template('profile.html', user_email=email, username=username)

# ------------------ SESSION USER ROUTE ------------------
@profile.route('/session-user')
def session_user():
    if 'email' in session:
        return jsonify({
            'email': session['email'],
            'username': session.get('username', 'Guest')
        })
    else:
        return jsonify({'error': 'Not logged in'}), 401
