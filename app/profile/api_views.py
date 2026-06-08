from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from . import profile
from ..models import db, User, Artwork, Favorite
from sqlalchemy.exc import IntegrityError, OperationalError

@profile.route('/me', methods=['GET'])
@jwt_required()
def get_my_profile():
    current_id = get_jwt_identity()
    user = User.query.get(current_id)
    if not user: return jsonify({ "message": "Пользователь не найден" }), 404
    artworks = user.artworks.order_by(Artwork.created_at.desc()).all()
    artworks_list = []
    for artwork in artworks:
        artworks_list.append({"id": artwork.id,
            "title": artwork.title,
            "description": artwork.description,
            "image_url": artwork.image_url,
            "width": artwork.width,
            "height": artwork.height})
    role_name = user.role.name if user.role else "user"
    return jsonify({ "id": user.id,
        "username": user.username,
        "email": user.email,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "role": user.role.name,
        "created_at": user.created_at,
        "artworks": artworks_list
         }), 200
@profile.route('/me', methods=['PUT'])
@jwt_required()
def update_profile():
    current_id = get_jwt_identity()
    user = User.query.get(current_id)
    if not user: return jsonify({"message": "Пользователь не найден"}), 404
    data = request.get_json()
    if not data:
        return jsonify({"message": "Запрос пустой"}), 400
    if data.get("username"): user.username = data["username"]
    if data.get("bio") is not None: user.bio = data["bio"]
    if data.get("avatar_url") is not None: user.avatar_url = data["avatar_url"]
    try:
        db.session.commit()
        return jsonify({"message": "Профиль обновлён" }), 200
    except IntegrityError:
        db.session.rollback()
        return jsonify({ "message": "Невозможно сохранить изменения"}), 409  # проблема в данных клиента, вероятный дубликат данных
    except OperationalError:
        db.session.rollback()
        return jsonify({"message": "Ошибка сервера"}), 500

@profile.route('/me', methods=['DELETE'])
@jwt_required()
def delete_profile():
    current_id = get_jwt_identity()
    user = User.query.get(current_id)
    if not user:
        return jsonify({"message": "Пользователь не найден"}), 404
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({ "message": "Аккаунт удалён" }), 200
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"message": "Невозможно удалить аккаунт","error": str(e.orig)}), 409
    except OperationalError as e:
        db.session.rollback()
        return jsonify({"message": "Ошибка сервера при удалении"}), 500
#чужой профиль с работами
@profile.route('/<string:username>', methods=['GET'])
def get_user_profile(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"message": "Пользователь не найден"}), 404
    artworks = user.artworks.order_by(Artwork.created_at.desc()).all()
    artworks_list =[]
    for artwork in artworks:
        artworks_list.append({
            "id": artwork.id,
            "title": artwork.title,
            "description": artwork.description,
            "image_url": artwork.image_url,
            "width": artwork.width,
            "height": artwork.height
        })
    return jsonify({"id": user.id,
        "username": user.username,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "role": user.role.name,
        "artworks": artworks_list}), 200

@profile.route('/me/favorites', methods=['GET'])
@jwt_required()
def get_my_favorites():
    current_id = get_jwt_identity()
    favorites = Favorite.query.filter_by(user_id=current_id).join(Artwork).all()
    result = []
    for favorite in favorites:
        artwork = favorite.artwork
        result.append({"id": artwork.id,
            "title": artwork.title,
            "image_url": artwork.image_url,
            "author": artwork.author.username})
    return jsonify(result), 200
