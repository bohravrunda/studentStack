from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from pymongo import MongoClient
import os

mail = Mail()
bcrypt = Bcrypt()
cors = CORS()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
