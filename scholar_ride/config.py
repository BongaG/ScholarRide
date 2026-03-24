import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'scholarride2026secretkey')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///scholarride.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAPTILER_KEY = os.getenv('MAPTILER_KEY')
    MAIL_DEFAULT_SENDER = ('ScholarRide', 'bongagazu10@gmail.com')
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=10)
    SESSION_PERMANENT = True