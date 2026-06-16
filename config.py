import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'glbtarfblr34r4mbort'
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ARTSPACE_MAIL_SUBJECT_PREFIX = '[ArtSpace]'
    ARTSPACE_MAIL_SENDER = 'ArtSpace Admin <artspace@mail.com>'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = 3600*24*90 #в сек, 90 дней до повторного входа

    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')

    @staticmethod
    def init_app(app):
        pass
class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'postgresql://postgres:postgres@localhost:5432/artspace_data'
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI ='sqlite:///:memory:'  # тестовая БД в памяти
    WTF_CSRF_ENABLED = False  # отлкючение CSRF для тестов

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.path.join(basedir, 'artspace.db')
    SQLALCHEMY_DATABASE_URI = os.path.join(basedir, 'artspace.db')

cloudinary.config(
    cloud_name=Config.CLOUDINARY_CLOUD_NAME,
    api_key=Config.CLOUDINARY_API_KEY,
    api_secret=Config.CLOUDINARY_API_SECRET,
    secure=True  # использует HTTPS
)

config = {'development': DevelopmentConfig,
            'testing': TestingConfig,
            'production': ProductionConfig,
            'default': DevelopmentConfig}
