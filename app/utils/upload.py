import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
# разрешённые расширения
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
def allowed_file(filename):
    #проверка расширения
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
#сохранение файла, возврат пути для БД
def save_file(file, folder):
    if not file or not allowed_file(file.filename):
        return None
    # генерация уникального имени
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    # полный путь
    folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder)
    file_path = os.path.join(folder_path, unique_filename)
    file.save(file_path)
    # относительный путь для БД вида avatars/example.jpg
    return f"{folder}/{unique_filename}"