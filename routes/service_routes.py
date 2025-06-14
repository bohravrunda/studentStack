from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from extensions import client

services = Blueprint('services', __name__)
services_collection = client['test'].services

@services.route('/create-service', methods=['POST'])
def create_service():
    try:
        form = request.form
        files = request.files.getlist('proof[]')

        file_paths = []
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')

        # Create upload folder if doesn't exist
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        for file in files:
            if file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                file_paths.append(filepath)

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
                'payment_method': form.getlist('payment_method')  # multiple methods
            },
            'level': form.get('level'),
            'language': form.getlist('language[]'),
            'portfolio_files': file_paths,
            'additional_note': form.get('additional_note'),
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

