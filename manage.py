import os
from app import create_app, db
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

if __name__ == '__main__':
    cli()