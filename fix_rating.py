# fix_ratings.py
from app import create_app
from app.db_create import db
from app.models import Artwork
from app.utils.rating import update_artwork_rating

app = create_app('development')
with app.app_context():
    artworks = Artwork.query.all()
    for artwork in artworks:
        update_artwork_rating(artwork.id)
        print(f"Работа {artwork.id}: рейтинг {artwork.rating}")

    db.session.commit()
