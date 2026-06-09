from sqlite3 import IntegrityError, OperationalError
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..utils.rating import update_artwork_rating
from . import likes
from app.db_create import db
from ..models import Artwork, Like

#эндпоинт, чтобы поставить отметку
@likes.route('/<int:artwork_id>', methods=['POST'])
@jwt_required()
def add_like(artwork_id):
    current_id = int(get_jwt_identity())
    artwork = Artwork.query.get(artwork_id)
    if artwork is None:
        return jsonify({ "message": "Работа не найдена" }), 404
    existing_like = Like.query.filter_by(user_id=current_id,artwork_id=artwork_id).first()
    if existing_like:
        return jsonify({"message": "Лайк уже поставлен"}), 400
    like = Like(user_id=current_id,artwork_id=artwork_id)
    try:
        db.session.add(like)
        db.session.commit()
        update_artwork_rating(artwork.user_id)
        return jsonify({"likes_count": artwork.likes.count()
        }), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Лайк уже поставлен"}), 400
    except OperationalError:
        db.session.rollback()
        return jsonify({"message": "Ошибка сервера"}), 500
#эндпоинт, чтобы удалить отметку
@likes.route('/<int:artwork_id>', methods=['DELETE'])
@jwt_required()
def remove_like(artwork_id):
    current_id = int(get_jwt_identity())
    like = Like.query.filter_by(user_id=current_id,artwork_id=artwork_id).first()
    if like is None:
        return jsonify({"message": "Лайк не найден"}), 404
    try:
        db.session.delete(like)
        db.session.commit()
        artwork = Artwork.query.get(artwork_id)
        return jsonify({"message": "Лайк удалён","likes_count": artwork.likes.count()}), 200
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Ошибка в данных"}), 400
    except OperationalError:
        db.session.rollback()
        return jsonify({"message": "Ошибка сервера"}), 500
#количество лайков
@likes.route('/<int:artwork_id>', methods=['GET'])
def get_likes_count(artwork_id):
    artwork = Artwork.query.get(artwork_id)
    if artwork is None: return jsonify({ "message": "Работа не найдена"}), 404
    return jsonify({ "artwork_id": artwork.id,
        "likes_count": artwork.likes.count()}), 200