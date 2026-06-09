from flask import Blueprint
likes = Blueprint('likes', __name__)
from . import api_views