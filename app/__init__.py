
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
from .authentification  import auth
from .comments import comments
from .news import news
migrate = Migrate()
mail = Mail()
jwt = JWTManager()

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    CORS(app,
         resources={r"/*": {"origins": "*"}},
         supports_credentials=True,
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"]) #разрешение на запросы с фронтенда
    config[config_name].init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    db.init_app(app)
    jwt.init_app(app)
    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(profile, url_prefix='/profile')
    app.register_blueprint(artworks, url_prefix='/artworks')
    app.register_blueprint(likes, url_prefix='/likes')
    app.register_blueprint(favorites, url_prefix='/favorites')
    app.register_blueprint(comments, url_prefix='/comments')
    app.register_blueprint(news, url_prefix='/news')

    @app.after_request
    def add_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:5173'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response
    # Обработка preflight OPTIONS запросов
    @app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
    @app.route('/<path:path>', methods=['OPTIONS'])
    def handle_options(path):
        response = app.make_response()
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:5173'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response
    return app