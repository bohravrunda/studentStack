from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from extensions import client
from flask import session


cart_bp = Blueprint('cart', __name__)
@cart_bp.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    service = request.json

    if 'cart' not in session:
        session['cart'] = []

    session['cart'].append(service)
    session.modified = True

    return jsonify({"message": "Service added to cart!", "cart": session['cart']}), 200

@cart_bp.route('/view-cart', methods=['GET'])
def view_cart():
    return jsonify(session.get('cart', []))

services = Blueprint('services', __name__)
services_collection = client['test'].services

@services.route('/create-service', methods=['POST'])
def create_service():
    try:
        form = request.form
        files = request.files.getlist('proof[]')
        thumbnail_file = request.files.get('thumbnail')  # Get thumbnail from request

        file_paths = []
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')

        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        # Save proof files
        for file in files:
            if file and file.filename != '':
                filename = secure_filename(file.filename.replace(" ", "_"))
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                file_paths.append(f'/uploads/{filename}')  # Save as browser path

        # Save thumbnail
        thumbnail_path = ''
        if thumbnail_file and thumbnail_file.filename != '':
            tn = secure_filename(thumbnail_file.filename)
            tn_path = os.path.join(upload_folder, tn)
            thumbnail_file.save(tn_path)
            thumbnail_path = f'/uploads/{tn}'  # For frontend access

        service_doc = {
            'user_id': form.get('userId'),
            'username': form.get('username'),
            'service_name': form.get('service_name'),
            'category': form.get('category'),
            'provider': {
                'name': form.get('provider_name'),
                'email': form.get('provider_email'),
                'location': form.get('provider_location')
            },
            'availability': {
                'from': form.get('starting_date'),
                'to': form.get('ending_date'),
                'days': form.getlist('available_days[]')
            },
            'cost': {
                'price': form.get('price'),
                'payment_method': form.getlist('payment_method')
            },
            'level': form.get('level'),
            'language': form.getlist('language[]'),
            'portfolio_files': file_paths,
            'additional_note': form.get('additional_note'),
            'thumbnail': thumbnail_path,
            'created_at': datetime.utcnow()
        }

        services_collection.insert_one(service_doc)
        return jsonify({'message': 'Service created successfully'}), 201

    except Exception as e:
        return jsonify({'error': 'Service creation failed', 'message': str(e)}), 500
@services.route('/search-services', methods=['GET'])
def search_services():
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'error': 'Search query is required'}), 400

        regex_query = {'$regex': query, '$options': 'i'}
        services_cursor = services_collection.find({
            '$or': [
                {'service_name': regex_query},
                {'provider.name': regex_query},
                {'category': regex_query}
            ]
        })

        services_list = []
        for service in services_cursor:
            service['_id'] = str(service['_id'])
            service['user_id'] = str(service.get('user_id', ''))
            services_list.append(service)

        return jsonify(services_list), 200
    except Exception as e:
        return jsonify({'error': 'Search failed', 'message': str(e)}), 500


@services.route('/get-services-by-userid', methods=['GET'])
def get_services_by_userid():
    try:
        user_id = request.args.get('userId')
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400

        services_cursor = services_collection.find({'user_id': user_id})
        services_list = [dict(service, _id=str(service['_id'])) for service in services_cursor]
        return jsonify(services_list), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch services', 'message': str(e)}), 500
    
@services.route('/get-all-services', methods=['GET'])
def get_all_services():
    try:
        services_cursor = services_collection.find()  # <-- yahan 'services_collection' use karo
        services_list = []
        for service in services_cursor:
            service['_id'] = str(service['_id'])
            service['user_id'] = str(service.get('user_id', ''))
            services_list.append(service)
        return jsonify(services_list), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch all services', 'message': str(e)}), 500

# -------------------- PROFILE --------------------

from bson import ObjectId

@services.route('/get-service', methods=['GET'])
def get_service_by_id():
    try:
        service_id = request.args.get('id')
        if not service_id:
            return jsonify({'error': 'Service ID is required'}), 400

        service = services_collection.find_one({'_id': ObjectId(service_id)})
        if not service:
            return jsonify({'error': 'Service not found'}), 404

        service['_id'] = str(service['_id'])  # Convert ObjectId to string
        service['user_id'] = str(service.get('user_id', ''))

        return jsonify(service), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch service', 'message': str(e)}), 500
