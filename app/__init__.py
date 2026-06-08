from flask import Flask
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import config
from .profile import profile
from .artworks import artworks
migrate = Migrate()
mail = Mail()
db = SQLAlchemy()
jwt = JWTManager()

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    CORS(app, supports_credentials=True) #разрешение на запросы с фронтенда
    config[config_name].init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    db.init_app(app)
    jwt.init_app(app)
    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')
    api.register_blueprint(profile, url_prefix='/profile')
    api.register_blueprint(artworks, url_prefix='/artworks')
    return app