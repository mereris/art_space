from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from . import comments
from  app.db_create import db
from ..models import User, Artwork, Comment

# добавление комментария

@comments.route('/<int:artwork_id>', methods=['POST'])
@jwt_required()
def add_comment(artwork_id):

    current_id = int(get_jwt_identity())
    artwork = Artwork.query.get(artwork_id)
    if artwork is None:
        return jsonify({"message": "Работа не найдена" }), 404
    data = request.get_json()
    if data is None:
        return jsonify({"message": "Пустой запрос" }), 400
    content = data.get('content')
    if content is None: return jsonify({"message": "Комментарий отсутствует" }), 400
    content = content.strip()
    if len(content) == 0:
        return jsonify({ "message": "Комментарий не может быть пустым" }), 400
    if len(content) > 1000:
        return jsonify({"message": "Комментарий слишком длинный" }), 400
    comment = Comment( user_id=current_id,
        artwork_id=artwork_id,
        content=content)
    try:
        db.session.add(comment)
        db.session.commit()
        return jsonify({"message": "Комментарий добавлен", "comment_id": comment.id}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({ "message": "Ошибка целостности данных" }), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"message": "Ошибка базы данных" }), 500

#получение всех комментариев к 1й работе
@comments.route('/<int:artwork_id>', methods=['GET'])
def get_comments(artwork_id):
    artwork = Artwork.query.get(artwork_id)
    if artwork is None:
        return jsonify({ "message": "Работа не найдена" }), 404
    comments_list = Comment.query.filter_by(artwork_id=artwork_id,is_hidden=False).order_by(Comment.created_at.asc()).all()
    result = []
    for comment in comments_list:
        result.append({"id": comment.id,
            "author": comment.user.username,
            "content": comment.content,
            "created_at": comment.created_at })
    return jsonify(result), 200

#удаление комментария самостоятельно
@comments.route('/comment/<int:comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(comment_id):
    current_id = int(get_jwt_identity())
    comment = Comment.query.get(comment_id)
    if comment is None:
        return jsonify({ "message": "Комментарий не найден" }), 404
    if comment.user_id != current_id:
        return jsonify({ "message": "Удалять комментарий может только его владелец" }), 403
    try:
        db.session.delete(comment)
        db.session.commit()
        return jsonify({"message": "Комментарий удалён"}), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"message": "Ошибка базы данных"}), 500

