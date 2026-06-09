
from flask import Flask
from flask_mail import Mail
from flask_migrate import Migrate
from .db_create import db
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import config
from .profile import profile
from .artworks import artworks
from .likes import likes
from .favorites import favorites
migrate = Migrate()
mail = Mail()
jwt = JWTManager()

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    CORS(app, origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ])    #разрешение на запросы с фронтенда
    config[config_name].init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    db.init_app(app)
    jwt.init_app(app)
    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')
    app.register_blueprint(profile, url_prefix='/profile')
    app.register_blueprint(artworks, url_prefix='/artworks')
    app.register_blueprint(likes, url_prefix='/likes')
    app.register_blueprint(favorites, url_prefix='/favorites')
    return app