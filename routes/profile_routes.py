from flask import Blueprint, request, jsonify
from datetime import datetime
from extensions import client

profile = Blueprint('profile', __name__)
profile_collection = client['test'].profile

@profile.route('/save-profile', methods=['POST'])
def save_profile():
    # [same logic]
    ...

@profile.route('/edit-profile', methods=['PUT'])
def edit_profile():
    # [same logic]
    ...

@profile.route('/get-profile', methods=['GET'])
def get_profile():
    # [same logic]
    ...
