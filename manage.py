import os
from flask import send_from_directory
from app import create_app
from app.db_create import db
from app.models import User, Role, Category, Artwork, Like, Favorite, Comment, News
from flask_migrate import Migrate
from flask.cli import FlaskGroup

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)
cli = FlaskGroup(create_app=lambda: app)

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role, Category=Category,
                Artwork=Artwork, Like=Like, Favorite=Favorite,
                Comment=Comment, News=News)

#путь в папку uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#отправка файлов
@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)