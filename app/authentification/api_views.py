from sqlite3 import IntegrityError, OperationalError
from flask import request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from . import auth
from app.db_create import db
from ..models import User, Role
from email_validator import validate_email, EmailNotValidError
@auth.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    try:
        check_deliverability = current_app.config.get('CHECK_EMAIL_DELIVERABILITY', True)
        email_info = validate_email(email, check_deliverability=check_deliverability)
    except EmailNotValidError as e:
        return jsonify({"message": f"Несуществующий адрес электронной почты: {str(e)}"}), 400
    username = data.get('username')
    password = data.get('password')
    role_name= data.get('role')
    possible_roles = ["Viewer", "Artist"]
    if role_name not in possible_roles:
        return jsonify({"message": "Недопустимая роль"}), 400
    confirm_password = data.get('confirm_password')
    if not all([email, username, password, role_name]):
        return jsonify({"message": "Все поля обязательны для заполнения"}), 400
    if password != confirm_password:
        return jsonify({"message": "Введенный пароль не совпадает с повторно введенным"}), 400
    if len(password) < 8:
        return jsonify({"message": "Пароль должен содержать минимум 8 символов"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Пользователь с таким email уже существует! "}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Никнейм уже занят"}), 409
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        return jsonify({"message": "Нет роли в БД/названа по-другому"}), 400
    user = User(email=email, username=username, role_id=role.id)
    user.password = password
    try:
        db.session.add(user)
        db.session.commit()
        access_token = create_access_token(identity=user.id)
        return jsonify({"message": "Пользователь успешно зарегистрирован! ", "access_token": access_token, }), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Пользователь с таким email или именем уже существует"}), 409
    except OperationalError:
        db.session.rollback()
        return jsonify({"message": "Ошибка сервера"}), 500

@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json() # "email": ..., "password": ...
    email = data.get('email')
    password = data.get('password')
    if not email:
        return jsonify({"message": "Пожалуйста, заполните поле для ввода электроннной почты"}), 400
    if not password:
        return jsonify({"message": "Пожалуйста, заполните поле для ввода пароля"}), 400
    try:
        user = User.query.filter_by(email=email.lower()).first()
    except OperationalError:
        # переподключение к БД
        db.session.rollback()
        db.session.remove()
        # 2 попытка
        user = User.query.filter_by(email=email.lower()).first()
    if user is not None and user.verify_password(password):
        token = create_access_token(identity=str(user.id))
        return jsonify({
            "access_token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }), 200

    return jsonify({"message": "Некорреткный эмейл иои пароль"}), 401

@auth.route('/me', methods=['GET'])
@jwt_required()
def get_profile():
    current_id = get_jwt_identity()
    user = User.query.get(current_id)
    if not user: #проверка, в случае если профиль удален, но токен рабочий
        return jsonify({"message": "Пользователь не найден"}), 404
    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email
    }), 200