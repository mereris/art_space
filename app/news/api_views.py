from flask import jsonify
from . import news
from ..models import News
#получение новостей
@news.route('', methods=['GET'])
def get_news():
    news_list = News.query.order_by(News.created_at.desc()).all()
    result = []
    for item in news_list:
        result.append({ "id": item.id,
            "title": item.title,
            "content": item.content,
            "event_date": item.event_date,
            "place": item.place,
            "created_at": item.created_at})
    return jsonify(result), 200