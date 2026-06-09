import os
from flask import current_app

def delete_file(relative_path):
    if not relative_path:
        return
    full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], relative_path)
    if os.path.exists(full_path):
        os.remove(full_path)