from flask import Flask, render_template,request, session, redirect, url_for
from extensions import mail, bcrypt, cors, client   # ✅ now works
from config import Config                            # ✅ now works
from routes.auth_routes import auth, google_bp
from routes.service_routes import services
from routes.profile_routes import profile
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

print("Current Working Directory:", os.getcwd())
print("Templates folder exists:", os.path.exists("templates"))
print("Index.html exists:", os.path.exists("templates/index.html"))



app = Flask(__name__, static_url_path='/static', static_folder='static')
print("Static folder path:", app.static_folder)
print("Static URL path:", app.static_url_path)
print("Static folder exists:", os.path.exists(app.static_folder))
app.config.from_object(Config)

# Register Extensions
mail.init_app(app)
bcrypt.init_app(app)
cors.init_app(app, supports_credentials=True)

# Mongo Client
client = client or client.from_uri(app.config['MONGO_URI'])

# Register Blueprints
app.register_blueprint(auth)
app.register_blueprint(google_bp, url_prefix="/login")
app.register_blueprint(services)
app.register_blueprint(profile)

@app.before_request
def require_login():
    # Allow access to static files and login/signup routes without session
    if request.path.startswith('/static') or request.path.startswith('/login/google'):
        return

    # List routes allowed without login
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


# Static Routes

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/signup.html')
def signup_page():
    return render_template('signup.html')

@app.route('/login.html')
def login_page():
    return render_template('login.html')


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


@app.route('/profile.html')
def profile_service():
    return render_template('profile.html')

# Run
if __name__ == '__main__':
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, host='0.0.0.0')
