from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import joinedload
import cloudinary


from ..utils.delete_files import delete_file
from ..utils.upload import save_file
from ..utils.rating import update_artwork_rating
from . import artworks
from app.db_create import db
from ..models import User, Artwork, Category, Tag, Like, Favorite
#загрузка картинки
@artworks.route('/upload-image', methods=['POST'])
@jwt_required()
def upload_artwork_image():
    current_id = int(get_jwt_identity())
    user = User.query.get(current_id)
    if not user or user.role.name != "Artist":
        return jsonify({"message": "Недостаточно прав"}), 403
    if 'file' not in request.files:
        return jsonify({"message": "Файл не отправлен"}), 400
    file = request.files['file']
    allowed_formats = {'png', 'jpg', 'jpeg', 'gif'}
    file_split = file.filename.rsplit('.', 1)[-1].lower()
    if file_split not in allowed_formats:
        return jsonify({"message": "Недопустимый формат файла"}), 400
    try:
        # ✅ ЗАГРУЗКА В CLOUDINARY
        upload_result = cloudinary.uploader.upload(file, folder=f"artworks/user_{current_id}",  # папка по user_id
            transformation=[ {'width': 1920, 'crop': 'limit'},  # ограничения размера
                {'quality': 'auto'},
                {'fetch_format': 'auto'}
            ]
        )
        image_url = upload_result['secure_url']
        public_id = upload_result['public_id']  # для удаления
        #  URL для сохранения в БД
        return jsonify({"message": "Изображение загружено",
            "image_url": image_url,
            "public_id": public_id
        }), 201
    except Exception as e: return jsonify({"message": f"Ошибка загрузки: {str(e)}"}), 500

#Создание работы
@artworks.route('', methods=['POST'])
@jwt_required()
def create_artwork():
    current_id = get_jwt_identity()
    user = User.query.get(current_id)
    if not user:
        return jsonify({"message": "Пользователь не найден"}), 404
    if user.role.name != "Artist": return jsonify({ "message": "Публикация доступна только художникам"}), 403
    data = request.get_json()
    if not data:
        return jsonify({"message": "Запрос пустой"}), 400
    title = data.get('title')
    description = data.get('description')
    image_url = data.get('image_url')
    category_id = data.get('category_id')
    if not category_id:
        return jsonify({"message": "Категория не найдена"}), 404
    tags = data.get('tags', [])
    width = data.get('width')
    height = data.get('height')
    if not all([title, image_url, category_id, width, height]):
        return jsonify({"message": "Не все обязательные поля заполнены"}), 400
    category = Category.query.get(category_id)
    if not category:
        return jsonify({"message": "Категория не найдена"}), 404
    artwork = Artwork(title=title,
        description=description,
        image_url=image_url,
        category_id=category_id,
        user_id=user.id,
        width=width,
        height = height
    )
    if tags is not None:
        if not isinstance(tags, list):
            return jsonify({"message": "Теги должны быть списком"}), 400
        for tag_name in data['tags']:
            if not isinstance(tag_name, str):
                continue
            tag_name = tag_name.replace('#', '').strip().lower()
            if not tag_name:
                continue
            tag = Tag.query.filter_by(name=tag_name).first()
            if tag is None:
                tag = Tag(name=tag_name)
                db.session.add(tag)
            artwork.tags.append(tag)
    try:
        db.session.add(artwork)
        db.session.commit()
        #обновление рейтинга текущей работы
        update_artwork_rating(artwork.id)
        #обновление рейтингов последних 5 работ
        old_artworks = Artwork.query.filter_by(user_id=user.id).order_by(Artwork.created_at.desc()).offset(1).limit(5).all()
        for old_art in old_artworks:
            update_artwork_rating(old_art.id)
        return jsonify({"message": "Работа успешно опубликована","artwork_id": artwork.id}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Ошибка целостности данных (возможно, дубликат)"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"message": "Ошибка сервера"}), 500
#получение 1й работы
@artworks.route('/<int:artwork_id>', methods=['GET'])
def get_artwork(artwork_id):
    artwork = Artwork.query.get(artwork_id)
    if artwork is None:
        return jsonify({ "message": "Работа не найдена" }), 404
    verify_jwt_in_request(optional=True)
    current_id = get_jwt_identity()
    is_liked = False
    is_favorite = False
    if current_id:
        is_liked = (Like.query.filter_by(user_id=int(current_id),artwork_id=artwork.id).first() is not None)
        is_favorite = (Favorite.query.filter_by(user_id=int(current_id),artwork_id=artwork.id).first() is not None
        )
    comments_list = []
    for comment in artwork.comments:
        comments_list.append({
            "id": comment.id,
            "content": comment.content,
            "author": comment.user.username,
            "created_at": comment.created_at.isoformat() if comment.created_at else None
        })
    return jsonify({"id": artwork.id,
        "title": artwork.title,
        "description": artwork.description,
        "image_url": artwork.image_url,
        "author": artwork.author.username,
        "category": artwork.category.name,

        "width": artwork.width,
        "height": artwork.height,

        "created_at": artwork.created_at,

        "is_liked": is_liked,
        "is_favorite": is_favorite,

        "comments": comments_list,
        "rating": artwork.rating,
        "likes_count": artwork.likes.count(),
        "comments_count": artwork.comments.count(),
        "tags": [ f"#{tag.name}" for tag in artwork.tags]
    }), 200
#галерея + фильтрация
@artworks.route('', methods=['GET'])
def get_all_artworks():
    try:
        # параметры пагинации
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 24, type=int)
        if per_page > 100:
            per_page = 100
        query = Artwork.query.options(joinedload(Artwork.author),
                                    joinedload(Artwork.category),
                                    joinedload(Artwork.tags))
        category_name = request.args.get('category')
        tag_name = request.args.get('tag')
        author = request.args.get('author')
        search = request.args.get('search')
        if category_name:
            category = Category.query.filter_by(name=category_name).first()
            if category:
                query = query.filter_by(category_id=category.id)
            else:
                return jsonify({"items": [], "total": 0, "page": page, "pages": 0}), 200
        if search:
            query = query.join(User).filter(db.or_(Artwork.title.ilike(f'%{search}%'),User.username.ilike(f'%{search}%')))
        min_rating = request.args.get('min_rating', type=float)
        sort_by = request.args.get('sort', 'newest')
        # хранение тегов без хештега
        if tag_name:
            tag = Tag.query.filter_by(name=tag_name.lower()).first()
            if tag:
                query = query.join(Artwork.tags).filter(Tag.name == tag_name)
            else:
                return jsonify({"items": [], "total": 0, "page": page, "pages": 0}), 200
        if min_rating is not None:
            if min_rating < 0 or min_rating > 5:
                return jsonify({"items": [], "total": 0, "page": page, "pages": 0}), 200
            query = query.filter(Artwork.rating >= min_rating)

        if sort_by == 'rating':
            query = query.order_by(Artwork.rating.desc())
        elif sort_by == 'oldest':
            query = query.order_by(Artwork.created_at.asc())
        else:
            query = query.order_by(Artwork.created_at.desc())
        artworks_list = query.paginate(page=page, per_page=per_page, error_out=False)
        result = []
        for artwork in artworks_list.items:
            # безопасное получение имени и техники
            author_name = artwork.author.username if artwork.author else "Unknown"
            category_name = artwork.category.name if artwork.category else "Uncategorized"
            # лайки через уже загруженную информацию
            likes_count = artwork.likes.count()
            result.append({"id": artwork.id,
                           "title": artwork.title,
                           "image_url": artwork.image_url,
                           "author": artwork.author.username,
                           "category": artwork.category.name,
                           "likes_count": likes_count,
                           "comments_count": artwork.comments.count(),
                           "tags": [f"#{tag.name}"for tag in artwork.tags]})
        return jsonify({ "items": result,
        "total":  artworks_list.total,
         "page":  artworks_list.page,
         "pages":  artworks_list.pages}), 200
    except OperationalError:
        return jsonify({"message": "Ошибка сервера при загрузке галереи"}), 500

@artworks.route('/<int:artwork_id>', methods=['PUT'])
@jwt_required()
def update_artwork(artwork_id):
    artwork = Artwork.query.get(artwork_id)
    if artwork is None:
        return jsonify({"message": "Работа не найдена"}), 404
    current_id = int(get_jwt_identity())
    if artwork.user_id != current_id:
        return jsonify({"message": "Недостаточно прав"}), 403
    data = request.get_json()
    if not data:
        return jsonify({"message": "Запрос пустой"}), 400
    if data.get('image_url') and data['image_url'] != artwork.image_url:
        old_url = artwork.image_url
        if 'cloudinary' in old_url:
            try:
                public_id = old_url.split('/upload/')[1].split('.')[0]
                cloudinary.uploader.destroy(public_id)
            except:
                pass
    if data.get('title'):artwork.title = data['title']
    if data.get('description') is not None: artwork.description = data['description']
    if data.get('image_url') is not None: artwork.image_url = data['image_url']
    if data.get('category_id'):
        category = Category.query.get(data['category_id'])
        if not category:
            return jsonify({"message": "Категория не найдена"}), 404
        artwork.category_id = data['category_id']
    if data.get('tags') is not None:
        if not isinstance(data['tags'], list):
            return jsonify({"message": "Теги должны быть списком"}), 400
        artwork.tags.clear()
        for tag_name in data['tags']:
            tag_name = tag_name.replace('#', '').lower()
            tag = Tag.query.filter_by(name=tag_name).first()
            if tag is None:
                tag = Tag(name=tag_name)
                db.session.add(tag)
            artwork.tags.append(tag)
    try:
        db.session.commit()
        return jsonify({ "message": "Работа обновлена"}), 200
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Ошибка целостности данных (возможно, неверная категория)"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"message": "Ошибка сервера"}), 500
#удаление работы
@artworks.route('/<int:artwork_id>', methods=['DELETE'])
@jwt_required()
def delete_artwork(artwork_id):
    artwork = Artwork.query.get(artwork_id)
    if artwork is None:
        return jsonify({"message": "Работа не найдена"}), 404
    current_id = int(get_jwt_identity())
    if artwork.user_id != current_id:return jsonify({"message": "Недостаточно прав"}), 403
    try:
        # Из URL public_id
        if 'cloudinary' in artwork.image_url:
            public_id = artwork.image_url.split('/upload/')[1].split('.')[0]
            cloudinary.uploader.destroy(public_id)
        db.session.delete(artwork)
        db.session.commit()
        return jsonify({"message": "Работа удалена"}), 200
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Невозможно удалить работу (существуют связанные записи)"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"message": "Ошибка сервера"}), 500
