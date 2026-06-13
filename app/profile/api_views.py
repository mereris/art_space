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
import cloudinary

def delete_from_cloudinary(image_url):
    if not image_url or 'cloudinary.com' not in image_url:
        return
    try:
       if '/upload/' in image_url:
            public_id = image_url.split('/upload/')[1].split('.')[0]
            # удаление версии если есть
            if public_id.startswith('v') and '/' in public_id:
                public_id = public_id.split('/', 1)[1]
            cloudinary.uploader.destroy(public_id)
    except Exception as e:
        print(f"Ошибка удаления из Cloudinary: {e}")

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
             "category": artwork.category.name,
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
    new_avatar_url = None
    if 'avatar' in request.files:
        file = request.files['avatar']
        allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        format = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if format not in allowed:
            return jsonify({"message": "Неподдерживаемый формат файла"}), 400
        try:
            upload_result = cloudinary.uploader.upload(file,
                folder=f"avatars/user_{current_id}",
                transformation=[ {'width': 400, 'height': 400, 'crop': 'fill'},  # квадратная аватарка
                    {'quality': 'auto'},
                    {'fetch_format': 'auto'}
                ]
            )
            new_avatar_url = upload_result['secure_url']
            if user.avatar_url and 'cloudinary.com' in user.avatar_url:
                delete_from_cloudinary(user.avatar_url)
        except Exception as e:
            return jsonify({"message": f"Ошибка загрузки аватарки: {str(e)}"}), 500
    data = {}
    if request.form:
        data = request.form.to_dict()
    elif request.is_json:
        data = request.get_json() or {}
    if data.get("username"):
        user.username = data["username"]
    if data.get("bio") is not None:
        user.bio = data["bio"]
    if new_avatar_url:
        user.avatar_url = new_avatar_url
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
        if user.avatar_url and 'cloudinary.com' in user.avatar_url:
            delete_from_cloudinary(user.avatar_url)
        for artwork in user.artworks:
            if artwork.image_url and 'cloudinary.com' in artwork.image_url:
                delete_from_cloudinary(artwork.image_url)
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
        "email": user.email,
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
    favorites = Favorite.query.filter_by(user_id=current_id).join(Artwork).paginate(page=page,per_page = per_page, error_out=False)
    result = []
    for favorite in favorites.items:
        artwork = favorite.artwork
        result.append({"id": artwork.id,
            "title": artwork.title,
            "image_url": artwork.image_url,
            "author": artwork.author.username})
    return jsonify(result), 200
