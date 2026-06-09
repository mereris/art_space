from flask import Blueprint
comments = Blueprint('comments', __name__)
from . import api_views