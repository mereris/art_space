
from faker import Faker
from sqlalchemy.exc import IntegrityError
import os
import requests
from app import create_app
from app.db_create import db
from app.models import User, Role, Artwork, Category, News
import random
from datetime import datetime
fake = Faker('ru_RU')
Faker.seed(67)


def download_test_image(filename, upload_dir, width=800, height=600):
    #случайное изображение с picsum.photos
    url = f"https://picsum.photos/{width}/{height}?random={random.randint(1, 10000)}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"  ✅ Скачано: {filename}")
        return True
    except Exception as e:
        print(f"  ❌ Ошибка скачивания {filename}: {e}")
        return False

def seed_database():
    app = create_app('development')
    with app.app_context():
        upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'artworks')
        os.makedirs(upload_dir, exist_ok=True)
        # Роли
        roles = ['Viewer', 'Artist']
        role_objects = {}
        for name in roles:
            role = Role.query.filter_by(name=name).first()
            if not role:
                role = Role(name=name)
                db.session.add(role)
            role_objects[name] = role
        db.session.flush()
        # Пользователи
        users = []
        for _ in range(10):
            user = User(username=fake.user_name(),
                email=fake.email(),
                bio=fake.text(max_nb_chars=20),
                role_id=role_objects[random.choice(roles)].id)
            user.password = 'test123456'
            db.session.add(user)
            users.append(user)
        db.session.flush()
        # Техники
        categories = ['Масло', 'Акварель', 'Акрил']
        cat_objects = {}
        for name in categories:
            category = Category.query.filter_by(name=name).first()
            if not category:
                category = Category(name=name)
                db.session.add(category)
            cat_objects[name] = category
        db.session.flush()
        """"# Работы
        for _ in range(50):
            artwork = Artwork(title=fake.sentence(nb_words=4),
                description=fake.paragraph(nb_sentences=3),
                image_url=f'/uploads/artworks/test_{random.randint(1, 5)}.jpg',
                width=random.randint(30, 100),
                height=random.randint(30, 100),
                user_id=random.choice(users).id,
                category_id=random.choice(list(cat_objects.values())).id
            )
            try:
                db.session.add(user)
                db.session.flush()  # проверка ошибки до commit
            except IntegrityError:
                db.session.rollback()
                continue
        db.session.commit()
        print(f"Загружено: {len(users)} пользователей, 50 работ")"""
        #cобытия
        events_data = [
            {
                "title": "Viennacontemporary 2026",
                "content": "Международная ярмарка современного искусства...",
                "place": "Вена, Австрия",
                "event_date": datetime(2026, 9, 18, 10, 0, 0)  # Начало события
            },
            {
                "title": "Contemporary Istanbul 2026",
                "content": "Международная ярмарка современного искусства в Турции...",
                "place": "Стамбул, Турция",
                "event_date": datetime(2026, 9, 23, 11, 0, 0)
            },
            {
                "title": "Estampa 2026",
                "content": "Международная ярмарка современного эстампа...",
                "place": "Мадрид, Испания",
                "event_date": datetime(2026, 9, 24, 10, 30, 0)
            }
        ]

        print("Загружаем новости/события...")
        for item in events_data:
            existing = News.query.filter_by(title=item["title"]).first()
            if not existing:
                news_item = News(**item) #распаковка словаря внрутри конструктора
                try:
                    db.session.add(news_item)
                    db.session.flush()
                except IntegrityError:
                    db.session.rollback()
                    continue
            #изображения
            artworks = []
            for i in range(50):
                filename = f"artwork_{i + 1}.jpg"
                # скачивание изображения
                isDownload = download_test_image(filename=filename,
                    upload_dir=upload_dir,
                    width=random.randint(600, 1200),
                    height=random.randint(400, 900)
                )
                if not isDownload:
                    continue  # если не скачалось

                artwork = Artwork( title=fake.sentence(nb_words=4),
                    description=fake.paragraph(nb_sentences=3),
                    image_url=f'/uploads/artworks/{filename}',
                    width=random.randint(30, 100),
                    height=random.randint(30, 100),
                    user_id=random.choice(users).id,
                    category_id=random.choice(list(cat_objects.values())).id
                )
                db.session.add(artwork)
                artworks.append(artwork)
        db.session.commit()

if __name__ == '__main__':
    seed_database()