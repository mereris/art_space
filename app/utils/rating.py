import math
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from ..models import User, Artwork, Like, db
alfa = 2.0  # вес популярности
beta = 10.0  # вес активности
K = 15.0
#расчёт рейтинга пользователя
def calculate_artwork_rating(artwork_id):
   # R = α·ln(1+L) + β·f, где
   # L = общее количество лайков
   # f = количество работ за последние 30 дней

   artwork = Artwork.query.get(artwork_id)
   if not artwork:
        return 0.0
    # подсчёт лайков
   likes_count = Like.query.filter_by(artwork_id=artwork_id).count()
   # логарифмическая нормализация
   likes_component = math.log(1 + likes_count)
   # частота публикаций
   author_id = artwork.user_id
   thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
   recent_artworks = Artwork.query.filter(Artwork.user_id == author_id,Artwork.created_at >= thirty_days_ago).count()
   print(f"Work {artwork_id}: likes={likes_count}, recent={recent_artworks}, created_at={artwork.created_at}")
   # промежуточный рейтинг
   temp_rating = (alfa * likes_component) + (beta * recent_artworks)
   #нормализация к 5-ти бальной шкале
   # Формула 5 * (temp / (temp + K)), где K - cложность получения 5
   rating = 5.0 * (temp_rating / (temp_rating + K))
   # Округляем до 1 знака после запятой (например, 4.5)
   return round(rating, 2)

   #обновление рейтинга
def update_artwork_rating(artwork_id):
    artwork = Artwork.query.get(artwork_id)
    if not artwork:
        return
    artwork.rating = calculate_artwork_rating(artwork_id)
    artwork.last_rating_update = datetime.now(timezone.utc)
    db.session.commit()
