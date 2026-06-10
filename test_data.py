from io import BytesIO
import requests
from PIL import Image
from faker import Faker
from sqlalchemy.exc import IntegrityError
from huggingface_hub import InferenceClient
import os
import cloudinary.uploader
import cloudinary
from app import create_app
from app.db_create import db
from app.models import User, Role, Artwork, Category, News
import random
from datetime import datetime

fake = Faker('ru_RU')
Faker.seed(67)
PROMPTS_BY_CATEGORY = {
    'Масло': ["oil painting"],
    'Акварель': ["watercolor painting"],
    'Акрил': ["acrylic painting"],
    'Смешанная техника': ["mixed media art"]
}
PROMTS_AVATAR =['artistic portrait', 'anime style portrait', 'fantasy portrait']
HF_TOKEN = os.getenv('HF_TOKEN', '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')
client = InferenceClient(token=HF_TOKEN)

def generate_image_by_prompt(folder, prompt=None, width=800, height=600):
    #Генерация через Hugging Face
    try:
        '''
        print(f" Генерация: {prompt[:60]}")
        image = client.text_to_image(
            prompt,model="black-forest-labs/FLUX.1-schnell",
            width=width,height=height
        )
        '''
        # Lorem Picsum
        url = f"https://picsum.photos/{width}/{height}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f" Ошибка HTTP ")
            return None, None
        if not response.headers.get('content-type', '').startswith('image/'):
            print(f" Ответ не изображение")
            return None, None
        image = Image.open(BytesIO(response.content))
        # сохранение в памяти (не на диск)
        image_bytes = BytesIO()
        image.save(image_bytes, format="JPEG", quality=90)
        image_bytes.seek(0)
        upload_result = cloudinary.uploader.upload(
            image_bytes,
            folder=folder,
            transformation=[
                {'quality': 'auto'},
                {'fetch_format': 'auto'}
            ]
        )
        print(f" ---cгенерировано: {upload_result['public_id']}")
        return upload_result['secure_url'], upload_result['public_id']
    except Exception as e:
        print(f" ошибка: {e}")
        return None, None

def seed_database():
    app = create_app('development')
    with app.app_context():
        with app.app_context():
            cloudinary.config(
                cloud_name=app.config.get('CLOUDINARY_CLOUD_NAME'),
                api_key=app.config.get('CLOUDINARY_API_KEY'),
                api_secret=app.config.get('CLOUDINARY_API_SECRET'),
                secure=True
            )
        # роли
        roles = ['Viewer', 'Artist']
        role_objects = {}
        for name in roles:
            role = Role.query.filter_by(name=name).first()
            if not role:
                role = Role(name=name)
                db.session.add(role)
            role_objects[name] = role
        db.session.flush()

        # пользователи
        users = []
        for i in range(50):
            username = fake.user_name()
            prompt = random.choice(PROMTS_AVATAR)
            avatar_url, avatar_public_id = generate_image_by_prompt(prompt=prompt,
                folder=f"avatars/seed_{username}",
                width=random.choice([400, 512, 600]),
                height=random.choice([400, 512, 600])
            )
            if not avatar_url:
                continue
            user = User(
                username=username,
                email=fake.email(),
                avatar_url=avatar_url,
                bio=fake.text(max_nb_chars=120),
                role_id=role_objects[random.choice(roles)].id
        )
            user.password = 'test123456'
            db.session.add(user)
            users.append(user)
            db.session.flush()

        # категории
        categories = ['Масло', 'Акварель', 'Акрил', 'Смешанная техника']
        cat_objects = {}
        for name in categories:
            category = Category.query.filter_by(name=name).first()
            if not category:
                category = Category(name=name)
                db.session.add(category)
            cat_objects[name] = category
        db.session.flush()

        # работы
        artworks = []
        artists = [user for user in users if user.role_id == role_objects['Artist'].id]

        if not artists:
            print("Нет художников для создания работ!")
        else:
            for i in range(50):
                # случайная категория
                category_name = random.choice(categories)
                category_obj = cat_objects[category_name]

                # промт для этой категории
                prompts = PROMPTS_BY_CATEGORY[category_name]
                prompt = random.choice(prompts)

                image_url, image_public_id = generate_image_by_prompt(
                    prompt=prompt,
                    folder=f"artworks/seed_artwork_{i + 1}",
                    width=random.choice([800, 1024, 1200]),
                    height=random.choice([600, 768, 900])
                )
                if not image_url:
                    continue
                artwork = Artwork(
                    title=fake.sentence(nb_words=4).capitalize(),
                    description=fake.paragraph(nb_sentences=3),
                    image_url=image_url,
                    width=random.randint(800, 1200),
                    height=random.randint(600, 900),
                    user_id=random.choice(users).id,
                    category_id=category_obj.id
                )
                db.session.add(artwork)
                artworks.append(artwork)
        db.session.commit()
        from app.utils.rating import update_artwork_rating
        for artwork in artworks:
            update_artwork_rating(artwork.id)
        print(f"\n создано работ: {len(artworks)}")

        # события
        events_data = [
            {
                "title": "Viennacontemporary 2026",
                "content": "Международная ярмарка современного искусства...",
                "place": "Вена, Австрия",
                "event_date": datetime(2026, 9, 18, 10, 0, 0)
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
        for item in events_data:
            existing = News.query.filter_by(title=item["title"]).first()
            if not existing:
                news_item = News(**item)
                try:
                    db.session.add(news_item)
                    db.session.flush()
                    print(f"  ✅ {item['title']}")
                except IntegrityError:
                    db.session.rollback()
                    continue

        db.session.commit()
        print("\n бд заполнена")
        print(f"   Пользователей: {User.query.count()}")
        print(f"   Работ: {Artwork.query.count()}")
        print(f"   Новостей: {News.query.count()}")


if __name__ == '__main__':
    seed_database()
