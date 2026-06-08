from flask import Blueprint
artworks = Blueprint('artworks', __name__)
from . import api_views