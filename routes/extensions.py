from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from pymongo import MongoClient

mail = Mail()
bcrypt = Bcrypt()
cors = CORS()
client = None
