from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from . import favorites
from app.db_create import db
from ..models import Artwork, Favorite
from sqlalchemy.exc import IntegrityError, OperationalError

#добавление в избранное
@favorites.route('/<int:artwork_id>', methods=['POST'])
@jwt_required()
def add_to_favorites(artwork_id):
    current_id = int(get_jwt_identity())
    artwork = Artwork.query.get(artwork_id)
    if artwork is None:
        return jsonify({"message": "Работа не найдена"}), 404
    existing_favorite = Favorite.query.filter_by(
        user_id=current_id,
        artwork_id=artwork_id
    ).first()
    if existing_favorite: return jsonify({"message": "Работа уже добавлена в избранное"}), 400
    favorite = Favorite(user_id=current_id, artwork_id=artwork_id)
    try:
        db.session.add(favorite)
        db.session.commit()
        favorites_count = Favorite.query.filter_by(user_id=current_id).count()
        return jsonify({"message": "Работа добавлена в избранное","favorites_count": favorites_count}), 201
    except IntegrityError:
        # два запроса одновременно
        db.session.rollback()
        return jsonify({"message": "Работа уже добавлена в избранное"}), 400
    except OperationalError:
        db.session.rollback()
        return jsonify({"message": "Ошибка сервера"}), 500

#удаление из избранного
@favorites.route('/<int:artwork_id>', methods=['DELETE'])
@jwt_required()
def remove_from_favorites(artwork_id):

    current_id = int(get_jwt_identity())
    favorite = Favorite.query.filter_by(user_id=current_id,artwork_id=artwork_id).first()
    if favorite is None:
        return jsonify({"message": "Работа не находится в избранном"}), 404
    try:
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({"message": "Работа удалена из избранного"}), 200
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Работа уже добавлена в избранное"}), 400
    except OperationalError:
        db.session.rollback()
        return jsonify({"message": "Ошибка сервера"}), 500