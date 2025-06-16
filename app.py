from flask import Flask, render_template, request, session, redirect, url_for
from extensions import mail, bcrypt, cors, client
from config import Config
from flask_session import Session  # <-- ✅ ADD THIS LINE

from routes.auth_routes import auth, google_bp
from routes.service_routes import services
from routes.profile_routes import profile
import os

# Allow insecure transport for OAuth during development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Debug prints
print("Current Working Directory:", os.getcwd())
print("Templates folder exists:", os.path.exists("templates"))
print("Index.html exists:", os.path.exists("templates/index.html"))

app = Flask(__name__, static_url_path='/static', static_folder='static')

print("Static folder path:", app.static_folder)
print("Static URL path:", app.static_url_path)
print("Static folder exists:", os.path.exists(app.static_folder))

# Load config
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SESSION_TYPE'] = 'filesystem'  # Store session in server
Session(app)



# Register extensions
mail.init_app(app)
bcrypt.init_app(app)
cors.init_app(app, supports_credentials=True)

# ✅ No need to reinitialize Mongo client here (handled in extensions.py)

# Register blueprints
app.register_blueprint(auth)
app.register_blueprint(google_bp, url_prefix="/login")
app.register_blueprint(services)
app.register_blueprint(profile)

# Routes allowed without login
@app.before_request
def require_login():
    if request.path.startswith('/static') or request.path.startswith('/login/google'):
        return

    allowed_routes = [
        'auth.login', 'auth.signup', 'auth.google_callback',
        'auth.verify_email', 'auth.serve_verification_page',
        'auth.request_otp', 'auth.reset_password_with_otp','forgot_password','verify_otp_page',
        'login_page', 'signup_page',  # your HTML routes
        'google.login',  # <- fixed
        'home'           # <- now properly separated
    ]
    if 'user_id' not in session and request.endpoint not in allowed_routes:
        return redirect(url_for('login_page'))

# Static HTML routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/index.html')
def index_page():
    return render_template('index.html')


@app.route('/signup.html')
def signup_page():
    return render_template('signup.html')

@app.route('/login.html')
def login_page():
    return render_template('login.html')



@app.route('/profile.html')
def profile_page():
    return render_template('profile.html')

@app.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')

@app.route('/verify_otp.html')
def verify_otp_page():
    return render_template('verify_otp.html')

@app.route('/createService.html')
def createservice_page():
    return render_template('createService.html')

@app.route('/createdservices.html')
def created_service():
    return render_template('createdservices.html')

@app.route('/view.html')
def view_service():
    return render_template('view.html')

@app.route('/service-detail.html')
def service_detail():
    return render_template('service-detail.html')

@app.route('/payment.html')
def payment_detail():
    return render_template('payment.html')
from flask import send_from_directory

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Run the app
if __name__ == '__main__':
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, host='0.0.0.0')
