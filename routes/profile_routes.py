from flask import Blueprint, request, jsonify
from extensions import client

profile = Blueprint('profile', __name__)
profile_collection = client['test'].profile  # Or use 'test' if you're using test db

# Route to save profile (CREATE)
@profile.route('/save-profile', methods=['POST'])
def save_profile():
    data = request.get_json()
    email = data.get("email")

    if profile_collection.find_one({"email": email}):
        return jsonify({"error": "Profile already exists."}), 409

    result = profile_collection.insert_one(data)
    return jsonify({"message": "Profile created successfully!", "id": str(result.inserted_id)}), 201

# Route to edit profile (UPDATE)
@profile.route('/edit-profile', methods=['PUT'])
def edit_profile():
    data = request.get_json()
    email = data.get("email")

    if not profile_collection.find_one({"email": email}):
        return jsonify({"error": "Profile not found."}), 404

    profile_collection.update_one({"email": email}, {"$set": data})
    return jsonify({"message": "Profile updated successfully!"}), 200

# Route to get profile (READ)
@profile.route('/get-profile', methods=['GET'])
def get_profile():
    email = request.args.get("userId")

    profile_data = profile_collection.find_one({"email": email}, {"_id": 0})
    if not profile_data:
        return jsonify({"error": "Profile not found."}), 404

    return jsonify(profile_data), 200
