import os

from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from flask import current_app
from ..utils.delete_files import delete_file
from ..utils.upload import save_file
from . import profile
from app.db_create import db
from ..models import User, Artwork, Favorite
from sqlalchemy.exc import IntegrityError, OperationalError

@profile.route('/me', methods=['GET'])
@jwt_required()
def get_my_profile():
    current_id = get_jwt_identity()
    user = User.query.get(current_id)
    if not user: return jsonify({ "message": "Пользователь не найден" }), 404
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 24, type=int)
    if per_page > 100:
        per_page = 100
    artworks = user.artworks.order_by(Artwork.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    artworks_list = []
    for artwork in artworks.items:
        artworks_list.append({"id": artwork.id,
            "title": artwork.title,
            "description": artwork.description,
            "image_url": artwork.image_url,
            "width": artwork.width,
            "height": artwork.height,
            "rating": artwork.rating})
    role_name = user.role.name if user.role else "user"
    return jsonify({ "id": user.id,
        "username": user.username,
        "email": user.email,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "role": user.role.name,
        "created_at": user.created_at,
        "artworks": artworks_list,
         }), 200
@profile.route('/me', methods=['PUT'])
@jwt_required()
def update_profile():
    current_id = get_jwt_identity()
    user = User.query.get(current_id)
    if not user: return jsonify({"message": "Пользователь не найден"}), 404
    new_avatar_path = None
    if 'avatar' in request.files:
        file = request.files['avatar']
        new_avatar_path = save_file(file, 'avatars')
        if not new_avatar_path:
            return jsonify({"message": "неподдерживаемый формат файла"}), 400
        # удаление старой аватарки
        if user.avatar_url:
            old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.avatar_url)
            if os.path.exists(old_path):
                os.remove(old_path)
    data = request.form.to_dict()
    if data.get("username"):
        user.username = data["username"]
    if data.get("bio") is not None:
        user.bio = data["bio"]
    if new_avatar_path:
        user.avatar_url = new_avatar_path
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
        delete_file(user.avatar_url)
        for artwork in user.artworks:
            delete_file(artwork.image_url)
        db.session.delete(user)
        db.session.commit()
        return jsonify({ "message": "Аккаунт удалён" }), 200
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"message": "Невозможно удалить аккаунт"}), 409
    except OperationalError as e:
        db.session.rollback()
        return jsonify({"message": "Ошибка сервера при удалении"}), 500
#чужой профиль с работами
@profile.route('/<string:username>', methods=['GET'])
def get_user_profile(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"message": "Пользователь не найден"}), 404
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    if per_page > 100:
        per_page = 100
    artworks = user.artworks.order_by(Artwork.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    artworks_list =[]
    for artwork in artworks.items:
        artworks_list.append({
            "id": artwork.id,
            "title": artwork.title,
            "description": artwork.description,
            "image_url": artwork.image_url,
            "width": artwork.width,
            "rating": artwork.rating,
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
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 32, type=int)
    if per_page > 100:
        per_page = 100
    favorites = Favorite.query.filter_by(user_id=current_id).join(Artwork).pagination(page=page,per_page = per_page, error_out=False)
    result = []
    for favorite in favorites.items:
        artwork = favorite.artwork
        result.append({"id": artwork.id,
            "title": artwork.title,
            "image_url": artwork.image_url,
            "author": artwork.author.username})
    return jsonify(result), 200
