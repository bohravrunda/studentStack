from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from extensions import client
from flask import session


import cloudinary
import cloudinary.uploader
import cloudinary.api



cloudinary.config(
  cloud_name = "dgdn8unw8",
  api_key = "222592816421541",
  api_secret = "QJhwPW655zO4t8vp17eAWlQdWSw",  # replace with actual secret
  secure = True
)








cart_bp = Blueprint('cart', __name__)

@cart_bp.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    service = request.json
    if not service:
        return jsonify({'error': 'Service data required'}), 400

    cart_item = {
        '_id': str(ObjectId()),  # always generate new id for cart item
        'name': service.get('service_name'),
        'price': float(service.get('cost', {}).get('price', 0)),
        'image': service.get('thumbnail', '/static/images/placeholder.png'),
        'instructor': service.get('provider', {}).get('name', 'Unknown'),
        'level': service.get('level', 'All Levels')
    }

    if 'cart' not in session:
        session['cart'] = []

    session['cart'].append(cart_item)
    session.modified = True

    return jsonify({'message': 'Service added to cart!', 'cart': session['cart']}), 200
@cart_bp.route('/view-cart', methods=['GET'])
def view_cart():
    return jsonify(session.get('cart', []))

@cart_bp.route('/remove-from-cart', methods=['POST'])
def remove_from_cart():
    data = request.json
    service_id = data.get('service_id')

    if 'cart' in session:
        # Skip items without _id (defensive coding)
        session['cart'] = [
            item for item in session['cart']
            if item.get('_id') != service_id
        ]
        session.modified = True
        return jsonify({'success': True}), 200

    return jsonify({'error': 'Cart not found'}), 400




@cart_bp.route('/cart-count')
def cart_count():
    cart = session.get('cart', [])
    return jsonify({'count': len(cart)})


services = Blueprint('services', __name__)
services_collection = client['test'].services

@services.route('/create-service', methods=['POST'])
def create_service():
    try:
        form = request.form
        files = request.files.getlist('proof[]')
        thumbnail_file = request.files.get('thumbnail')

        file_paths = []
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        # Save proof files locally
        # Upload proof files to Cloudinary

        for file in files:
            if file and file.filename != '':
                upload_result = cloudinary.uploader.upload(file)
                file_paths.append(upload_result.get('secure_url'))


        # Upload thumbnail to Cloudinary
        thumbnail_url = ''
        if thumbnail_file and thumbnail_file.filename != '':
            upload_result = cloudinary.uploader.upload(thumbnail_file)
            thumbnail_url = upload_result.get('secure_url')

        # Insert into MongoDB
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
            'thumbnail': thumbnail_url,
            'created_at': datetime.utcnow()
        }

        services_collection.insert_one(service_doc)
        return jsonify({'message': 'Service created successfully'}), 201

    except Exception as e:
        return jsonify({'error': 'Service creation failed', 'message': str(e)}), 500


@services.route('/edit-service', methods=['PUT'])
def edit_service():
    try:
        service_id = request.form.get('id') or request.args.get('id')
        if not service_id:
            return jsonify({'error': 'Service ID is required'}), 400

        form = request.form
        files = request.files.getlist('proof[]')
        thumbnail_file = request.files.get('thumbnail')

        file_paths = []
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        # Save proof files locally
# Upload proof files to Cloudinary








        for file in files:
            if file and file.filename != '':
                upload_result = cloudinary.uploader.upload(file)
                file_paths.append(upload_result.get('secure_url'))

        # Upload thumbnail to Cloudinary
        thumbnail_url = None
        if thumbnail_file and thumbnail_file.filename != '':
            upload_result = cloudinary.uploader.upload(thumbnail_file)
            thumbnail_url = upload_result.get('secure_url')

        # Update document
        update_doc = {
            'service_name': form.get('service_name'),
            'category': form.get('category'),
            'provider.name': form.get('provider_name'),
            'provider.email': form.get('provider_email'),
            'provider.location': form.get('provider_location'),
            'availability.from': form.get('starting_date'),
            'availability.to': form.get('ending_date'),
            'availability.days': form.getlist('available_days[]'),
            'cost.price': form.get('price'),
            'cost.payment_method': form.getlist('payment_method'),
            'level': form.get('level'),
            'language': form.getlist('language[]'),
            'additional_note': form.get('additional_note')
        }

        if file_paths:
            update_doc['portfolio_files'] = file_paths
        if thumbnail_url:
            update_doc['thumbnail'] = thumbnail_url

        update_doc = {k: v for k, v in update_doc.items() if v is not None}

        result = services_collection.update_one(
            {'_id': ObjectId(service_id)},
            {'$set': update_doc}
        )

        if result.matched_count == 0:
            return jsonify({'error': 'Service not found'}), 404

        return jsonify({'message': 'Service updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': 'Failed to update service', 'message': str(e)}), 500
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


@services.route('/service/<service_id>', methods=['GET'])
def get_service(service_id):
    try:
        service = services_collection.find_one({'_id': ObjectId(service_id)})
        if not service:
            return jsonify({'message': 'Service not found'}), 404

        # Convert ObjectId to string for JSON response
        service['_id'] = str(service['_id'])
        return jsonify(service)
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@services.route('/delete-file', methods=['POST'])
def delete_file():
    try:
        data = request.get_json()
        service_id = data.get('service_id')
        file_type = data.get('file_type')

        # Debug: print incoming data
        print("Received service_id:", service_id)
        print("Received file_type:", file_type)

        if not service_id or not file_type:
            return jsonify({'error': 'Service ID and file type required'}), 400

        try:
            obj_id = ObjectId(service_id)
        except Exception as e:
            print("Invalid ObjectId:", e)
            return jsonify({'error': 'Invalid service ID'}), 400

        services_col = client['studentstack']['services']
        service = services_col.find_one({'_id': obj_id})

        if not service:
            print("Service not found for ID:", obj_id)
            return jsonify({'error': 'Service not found'}), 404

        file_path = None
        update = {}

        if file_type == 'thumbnail':
            file_path = service.get('thumbnail')
            update = {'$unset': {'thumbnail': ""}}

        elif file_type == 'portfolio':
            file_paths = service.get('portfolio_files', [])
            if file_paths:
                file_path = file_paths[0]  # ⚠ Or choose based on frontend input
                new_files = file_paths[1:]
                if new_files:
                    update = {'$set': {'portfolio_files': new_files}}
                else:
                    update = {'$unset': {'portfolio_files': ""}}
            else:
                return jsonify({'error': 'No portfolio file to delete'}), 400

        else:
            return jsonify({'error': 'Invalid file type'}), 400

        # Remove file from server
        if file_path:
            # Convert browser path to filesystem path
            filepath_on_disk = os.path.join(current_app.root_path, file_path.strip('/'))
            print("Attempting to remove file:", filepath_on_disk)

            if os.path.exists(filepath_on_disk):
                try:
                    os.remove(filepath_on_disk)
                    print("File removed:", filepath_on_disk)
                except Exception as e:
                    return jsonify({'error': f'File removal failed: {str(e)}'}), 500
            else:
                print("File not found on disk:", filepath_on_disk)

        # Update DB
        services_col.update_one({'_id': obj_id}, update)

        return jsonify({'message': 'File deleted successfully'}), 200

    except Exception as e:
        print("Exception in delete_file:", str(e))
        return jsonify({'error': 'Server error', 'message': str(e)}), 500
