import unittest
import uuid
from datetime import datetime, timezone

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from app import create_app
from app.db_create import db
from app.models import User, Role, Category, Artwork, Tag, Like, Favorite, Comment, News

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
#базовый класс для всех тестов
class BaseTests(unittest.TestCase):
#стартовые настройки
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        with db.engine.connect() as conn:
            conn.execute(db.text("PRAGMA foreign_keys=ON"))
            conn.commit()
        # роли по умолчанию
        self.role_viewer = Role(name='Viewer')
        self.role_artist = Role(name='Artist')
        db.session.add_all([self.role_viewer, self.role_artist])
        db.session.commit()
#очистка после каждого теста
    def tearDown(self):
        db.session.rollback()
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    def _create_user(self, username=None, email=None,
                 password='test123456', role=None):
        #создание пользователя
        if role is None:
            role = self.role_viewer
        unique_id = uuid.uuid4().hex[:8]
        user = User(username=username or f'testuser_{unique_id}',
            email=email or f'test_{unique_id}@example.com',
            bio='Test bio',
            role_id=role.id)
        user.password = password
        db.session.add(user)
        db.session.commit()
        return user

    def _create_category(self, name='Масло'):
        #создание категории
        category = Category(name=name)
        db.session.add(category)
        db.session.commit()
        return category

    def _create_artwork(self, user=None, category=None, title='Test Artwork'):
        #создание работы
        if user is None:
            user = self._create_user()
        if category is None:
            category = self._create_category()
        artwork = Artwork(title=title,
            description='Тестовое описание',
            image_url='/static/uploads/artworks/test.jpg',
            width=100,
            height=80,
            user_id=user.id,
            category_id=category.id)
        db.session.add(artwork)
        db.session.commit()
        return artwork
#тестирование Role
class RoleModelTests(BaseTests):

    def test_role_creation(self):
        #тест создания роли
        role = Role(name='Moderator')
        db.session.add(role)
        db.session.commit()
        self.assertIsNotNone(role.id)
        self.assertEqual(role.name, 'Moderator')

    # тест на уникальность имени роли
    def test_role_unique_name(self):
        role1 = Role(name='TestRole')
        db.session.add(role1)
        db.session.commit()
        role2 = Role(name='TestRole')
        db.session.add(role2)
        with self.assertRaises(IntegrityError):
            db.session.commit()

    #тест связи Role с User
    def test_role_users_relationship(self):
        user1 = self._create_user(username='user1', email='u1@example.com')
        user2 = self._create_user(username='user2', email='u2@example.com')
        self.assertEqual(self.role_viewer.users.count(), 2)
        self.assertIn(user1, self.role_viewer.users.all())
        self.assertIn(user2, self.role_viewer.users.all())
    def test_role_repr(self):
        self.assertEqual(repr(self.role_viewer), "<Role 'Viewer'>")

# тестирование User
class UserModelTests(BaseTests):
    # пароль хешируется при установке
    def test_password_setter(self):
        u = self._create_user()
        self.assertIsNotNone(u.password_hash)
        # настоящий пароль не должен храниться
        self.assertNotEqual(u.password_hash, 'test1234')

    # нельзя прочитать пароль
    def test_no_password_getter(self):
        u = self._create_user()
        with self.assertRaises(AttributeError):
            _ = u.password
    #проверка пароля
    def test_password_verification(self):
        u = self._create_user(password='passwordik')
        self.assertTrue(u.verify_password('passwordik'))
        self.assertFalse(u.verify_password('password'))
    #разные хеши одинаковых паролей
    def test_password_salts_are_random(self):
        u1 = self._create_user(username='u1', email='u1@example.com', password='var')
        u2 = self._create_user(username='u2', email='u2@example.com', password='var')
        self.assertNotEqual(u1.password_hash, u2.password_hash)
    #уникальность почты
    def test_unique_email(self):
        self._create_user(username='u1', email='artspace@example.com')
        u2 = User(username='u2', email='artspace@example.com', role_id=self.role_viewer.id)
        u2.password = 'test1234'
        db.session.add(u2)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        # уникальность никнейма
    def test_unique_username(self):
        self._create_user(username='user', email='u1@example.com')
        u2 = User(username='user', email='u2@example.com', role_id=self.role_viewer.id)
        u2.password = 'test123456'
        db.session.add(u2)
        with self.assertRaises(IntegrityError):
            db.session.commit()

    def test_user_creation_timestamp(self):
        u = self._create_user()
        self.assertIsNotNone(u.created_at)

    # тест связи User с Role
    def test_user_role_relationship(self):
        u = self._create_user()
        self.assertEqual(u.role.name, 'Viewer')
        self.assertEqual(u.role_id, self.role_viewer.id)
    #запись в поле avatar_url
    def test_user_avatar_url(self):
        u = self._create_user()
        u.avatar_url = '/static/uploads/avatars/test.png'
        db.session.commit()
        u_from_db = User.query.get(u.id)
        self.assertEqual(u_from_db.avatar_url, '/static/uploads/avatars/test.png')
    #запись в поле bio
    def test_user_bio(self):
        u = self._create_user()
        self.assertEqual(u.bio, 'Test bio')
    #строковое представление
    def test_user_repr(self):
        u = self._create_user(username='john')
        self.assertEqual(repr(u), "<User 'john'>")
    #рольобязательна для пользователя
    def test_user_without_role_fails(self):
        u = User(username='norole', email='norole@example.com')
        u.password = 'test123456'
        db.session.add(u)
        with self.assertRaises(IntegrityError):
            db.session.commit()
# тестирование Category
class CategoryModelTests (BaseTests):
    # создание
    def test_category_creation(self):
        cat = self._create_category('Акварель')
        self.assertIsNotNone(cat.id)
        self.assertEqual(cat.name, 'Акварель')
    #уникальность имени
    def test_category_unique_name(self):
        self._create_category('Масло')

        cat2 = Category(name='Масло')
        db.session.add(cat2)
        with self.assertRaises(IntegrityError):
            db.session.commit()
    #связь Category -> Artwork
    def test_category_artworks_relationship(self):
        user = self._create_user()
        cat = self._create_category()
        a1 = self._create_artwork(user=user, category=cat, title='Art 1')
        a2 = self._create_artwork(user=user, category=cat, title='Art 2')

        self.assertEqual(cat.artworks.count(), 2)
        self.assertIn(a1, cat.artworks.all())
        self.assertIn(a2, cat.artworks.all())
    # строковое представление
    def test_category_repr(self):
        cat = self._create_category('Акрил')
        self.assertEqual(repr(cat), '<Category Акрил>')
#тестирование Tag
class TagModelTests(BaseTests):
    #создание
    def test_tag_creation(self):
        tag = Tag(name='пейзаж')
        db.session.add(tag)
        db.session.commit()
        self.assertIsNotNone(tag.id)
        self.assertEqual(tag.name, 'пейзаж')
    #уникальность имени
    def test_tag_unique_name(self):
        tag1 = Tag(name='портрет')
        db.session.add(tag1)
        db.session.commit()
        tag2 = Tag(name='портрет')
        db.session.add(tag2)
        with self.assertRaises(IntegrityError):
            db.session.commit()

# тестирование Artwork
class ArtworkTests(BaseTests):
    # создание работы
    def test_artwork_creation(self):
        artwork = self._create_artwork()
        self.assertIsNotNone(artwork.id)
        self.assertEqual(artwork.title, 'Test Artwork')
        self.assertEqual(artwork.description, 'Тестовое описание')
    # обязательные поля (без title — ошибка)
    def test_artwork_required_fields(self):
        user = self._create_user()
        cat = self._create_category()
        artwork = Artwork(description='description',
            image_url='/test.jpg',
            user_id=user.id,
            category_id=cat.id)
        db.session.add(artwork)
        with self.assertRaises(IntegrityError):
            db.session.commit()
    # image_url обязательное
    def test_artwork_image_url_required(self):
        user = self._create_user()
        cat = self._create_category()
        artwork = Artwork(title='Test',
            description='description',
            user_id=user.id,
            category_id=cat.id)
        db.session.add(artwork)
        with self.assertRaises(IntegrityError):
            db.session.commit()
    # связь Artwork -> User (author)
    def test_artwork_author_relationship(self):
        user = self._create_user()
        artwork = self._create_artwork(user=user)
        self.assertEqual(artwork.author.id, user.id)
        self.assertEqual(artwork.author.username, user.username)
        self.assertIn(artwork, user.artworks.all())
    # связь Artwork -> Category
    def test_artwork_category_relationship(self):
        cat = self._create_category('Акварель')
        artwork = self._create_artwork(category=cat)
        self.assertEqual(artwork.category.id, cat.id)
        self.assertEqual(artwork.category.name, 'Акварель')
    # связь Artwork <-> Tag (many-to-many)
    def test_artwork_tags_relationship(self):
        artwork = self._create_artwork()
        tag1 = Tag(name='пейзаж')
        tag2 = Tag(name='масло')
        db.session.add_all([tag1, tag2])
        artwork.tags.extend([tag1, tag2])
        db.session.commit()
        self.assertEqual(len(artwork.tags), 2)
        self.assertIn(tag1, artwork.tags)
        self.assertIn(tag2, artwork.tags)
        # проверяем обратную связь
        self.assertIn(artwork, tag1.artworks)
        self.assertIn(artwork, tag2.artworks)
    # created_at устанавливается автоматически
    def test_artwork_timestamp(self):
        artwork = self._create_artwork()
        self.assertIsNotNone(artwork.created_at)
    # размеры работы
    def test_artwork_dimensions(self):
        artwork = self._create_artwork()
        self.assertEqual(artwork.width, 100)
        self.assertEqual(artwork.height, 80)
    # рейтинг по умолчанию 0.0
    def test_artwork_default_rating(self):
        artwork = self._create_artwork()
        self.assertEqual(artwork.rating, 0.0)
    # строковое представление
    def test_artwork_repr(self):
        user = self._create_user(username='artist')
        artwork = self._create_artwork(user=user, title='Вау')
        self.assertIn('Вау', repr(artwork))
        self.assertIn('artist', repr(artwork))

    # при удалении пользователя удаляются его работы
    def test_artwork_cascade_delete_with_user(self):
        user = self._create_user()
        artwork = self._create_artwork(user=user)
        artwork_id = artwork.id
        db.session.delete(user)
        db.session.commit()
        self.assertIsNone(db.session.get(Artwork, artwork_id))
    # размеры могут быть None
    def test_artwork_optional_dimensions(self):
        user = self._create_user()
        cat = self._create_category()
        artwork = Artwork( title='Красивая',
            description='desc',
            image_url='/test.jpg',
            user_id=user.id,
            category_id=cat.id
            # width и height не указаны
        )
        db.session.add(artwork)
        db.session.commit()
        self.assertIsNone(artwork.width)
        self.assertIsNone(artwork.height)

# тестирование лайков
class LikeTests(BaseTests):

    # создание лайка
    def test_like_creation(self):
        user = self._create_user()
        artwork = self._create_artwork()
        like = Like(user_id=user.id, artwork_id=artwork.id)
        db.session.add(like)
        db.session.commit()
        self.assertIsNotNone(like.id)
        self.assertIsNotNone(like.created_at)

    # один пользователь может лайкнуть работу только один раз
    def test_like_unique_constraint(self):
        user = self._create_user()
        artwork = self._create_artwork()
        like1 = Like(user_id=user.id, artwork_id=artwork.id)
        db.session.add(like1)
        db.session.commit()
        like2 = Like(user_id=user.id, artwork_id=artwork.id)
        db.session.add(like2)
        with self.assertRaises(IntegrityError):
            db.session.commit()

    # разные пользователи могут лайкать одну работу
    def test_multiple_users_can_like_same_artwork(self):
        user1 = self._create_user(username='u1', email='u1@example.com')
        user2 = self._create_user(username='u2', email='u2@example.com')
        artwork = self._create_artwork()
        like1 = Like(user_id=user1.id, artwork_id=artwork.id)
        like2 = Like(user_id=user2.id, artwork_id=artwork.id)
        db.session.add_all([like1, like2])
        db.session.commit()
        self.assertEqual(Like.query.filter_by(artwork_id=artwork.id).count(), 2)

    # один пользователь может лайкать разные работы
    def test_user_can_like_different_artworks(self):
        user = self._create_user()
        cat = self._create_category()
        a1 = self._create_artwork(user=user, category=cat, title='Art 1')
        a2 = self._create_artwork(user=user, category=cat, title='Art 2')
        liker = self._create_user(username='liker', email='liker@example.com')
        like1 = Like(user_id=liker.id, artwork_id=a1.id)
        like2 = Like(user_id=liker.id, artwork_id=a2.id)
        db.session.add_all([like1, like2])
        db.session.commit()
        self.assertEqual(liker.likes.count(), 2)

    # связи Like -> User и Like -> Artwork
    def test_like_relationships(self):
        user = self._create_user()
        artwork = self._create_artwork()
        like = Like(user_id=user.id, artwork_id=artwork.id)
        db.session.add(like)
        db.session.commit()
        self.assertEqual(like.user.id, user.id)
        self.assertEqual(like.artwork.id, artwork.id)

    # лайки удаляются при удалении пользователя
    def test_like_cascade_delete_user(self):
        user = self._create_user()
        artwork = self._create_artwork()
        like = Like(user_id=user.id, artwork_id=artwork.id)
        db.session.add(like)
        db.session.commit()
        like_id = like.id
        db.session.delete(user)
        db.session.commit()
        self.assertIsNone(Like.query.get(like_id))
    # лайки удаляются при удалении работы
    def test_like_cascade_delete_artwork(self):
        user = self._create_user()
        artwork = self._create_artwork()
        artwork_id=artwork.id
        like = Like(user_id=user.id, artwork_id=artwork.id)
        db.session.add(like)
        db.session.commit()
        like_id = like.id
        db.session.delete(artwork)
        db.session.commit()
        self.assertIsNone(Like.query.get(like_id))

# тестирование избранного
class FavoriteTests(BaseTests):

    # создание избранного
    def test_favorite_creation(self):
        user = self._create_user()
        artwork = self._create_artwork()
        fav = Favorite(user_id=user.id, artwork_id=artwork.id)
        db.session.add(fav)
        db.session.commit()
        self.assertIsNotNone(fav.id)
        self.assertIsNotNone(fav.created_at)

    # нельзя добавить одну работу в избранное дважды
    def test_favorite_unique_constraint(self):
        user = self._create_user()
        artwork = self._create_artwork()
        fav1 = Favorite(user_id=user.id, artwork_id=artwork.id)
        db.session.add(fav1)
        db.session.commit()
        fav2 = Favorite(user_id=user.id, artwork_id=artwork.id)
        db.session.add(fav2)
        with self.assertRaises(IntegrityError):
            db.session.commit()

    # связь User -> Favorites
    def test_user_favorites_relationship(self):
        user = self._create_user()
        cat = self._create_category()
        a1 = self._create_artwork(user=user, category=cat, title='Art 1')
        a2 = self._create_artwork(user=user, category=cat, title='Art 2')
        viewer = self._create_user(username='viewer', email='v@example.com')
        fav1 = Favorite(user_id=viewer.id, artwork_id=a1.id)
        fav2 = Favorite(user_id=viewer.id, artwork_id=a2.id)
        db.session.add_all([fav1, fav2])
        db.session.commit()
        self.assertEqual(viewer.favorites.count(), 2)

    # избранное удаляется при удалении работы
    def test_favorite_cascade_delete(self):
        user = self._create_user()
        artwork = self._create_artwork()
        fav = Favorite(user_id=user.id, artwork_id=artwork.id)
        db.session.add(fav)
        db.session.commit()
        fav_id = fav.id
        db.session.delete(artwork)
        db.session.commit()
        self.assertIsNone(Favorite.query.get(fav_id))

# тестирование комментариев
class CommentTests(BaseTests):
    # создание комментария
    def test_comment_creation(self):
        user = self._create_user()
        artwork = self._create_artwork()
        comment = Comment(user_id=user.id,
            artwork_id=artwork.id,
            content='Отличная работа!')
        db.session.add(comment)
        db.session.commit()
        self.assertIsNotNone(comment.id)
        self.assertEqual(comment.content, 'Отличная работа!')
        self.assertFalse(comment.is_hidden)
    # content обязателен
    def test_comment_content_required(self):
        user = self._create_user()
        artwork = self._create_artwork()
        comment = Comment(user_id=user.id,
            artwork_id=artwork.id
            # content не указан
        )
        db.session.add(comment)
        with self.assertRaises(IntegrityError):
            db.session.commit()

    # is_hidden по умолчанию False
    def test_comment_default_is_hidden(self):
        user = self._create_user()
        artwork = self._create_artwork()
        comment = Comment(user_id=user.id,
            artwork_id=artwork.id,
            content='Test')
        db.session.add(comment)
        db.session.commit()
        self.assertFalse(comment.is_hidden)

    # комментарий можно скрыть
    def test_comment_can_be_hidden(self):
        user = self._create_user()
        artwork = self._create_artwork()
        comment = Comment(user_id=user.id,
            artwork_id=artwork.id,
            content='Test',
            is_hidden=True)
        db.session.add(comment)
        db.session.commit()
        self.assertTrue(comment.is_hidden)

    # created_at устанавливается автоматически
    def test_comment_timestamp(self):
        user = self._create_user()
        artwork = self._create_artwork()
        comment = Comment(user_id=user.id,
            artwork_id=artwork.id,
            content='Test')
        db.session.add(comment)
        db.session.commit()
        self.assertIsNotNone(comment.created_at)
    # связи Comment -> User и Comment -> Artwork
    def test_comment_relationships(self):
        user = self._create_user(username='commenter')
        artwork = self._create_artwork(title='Art')
        comment = Comment( user_id=user.id,
            artwork_id=artwork.id,
            content='Супер!')
        db.session.add(comment)
        db.session.commit()
        self.assertEqual(comment.user.username, 'commenter')
        self.assertEqual(comment.artwork.title, 'Art')
    # связь User -> Comments
    def test_user_comments_relationship(self):
        user = self._create_user()
        artwork = self._create_artwork()
        c1 = Comment(user_id=user.id, artwork_id=artwork.id, content='Comment 1')
        c2 = Comment(user_id=user.id, artwork_id=artwork.id, content='Comment 2')
        db.session.add_all([c1, c2])
        db.session.commit()
        self.assertEqual(user.comments.count(), 2)
    # связь Artwork -> Comments
    def test_artwork_comments_relationship(self):
        user = self._create_user()
        artwork = self._create_artwork()
        c1 = Comment(user_id=user.id, artwork_id=artwork.id, content='Comment 1')
        c2 = Comment(user_id=user.id, artwork_id=artwork.id, content='Comment 2')
        db.session.add_all([c1, c2])
        db.session.commit()
        self.assertEqual(artwork.comments.count(), 2)
    # комментарии удаляются при удалении пользователя
    def test_comment_cascade_delete_user(self):
        user = self._create_user()
        artwork = self._create_artwork()
        comment = Comment(user_id=user.id, artwork_id=artwork.id, content='Test')
        db.session.add(comment)
        db.session.commit()
        comment_id = comment.id
        db.session.delete(user)
        db.session.commit()
        self.assertIsNone(Comment.query.get(comment_id))
    # комментарии удаляются при удалении работы
    def test_comment_cascade_delete_artwork(self):
        user = self._create_user()
        artwork = self._create_artwork()
        comment = Comment(user_id=user.id, artwork_id=artwork.id, content='Test')
        db.session.add(comment)
        db.session.commit()
        comment_id = comment.id
        db.session.delete(artwork)
        db.session.commit()
        self.assertIsNone(Comment.query.get(comment_id))
    # строковое представление
    def test_comment_repr(self):
        user = self._create_user(username='Ivan')
        artwork = self._create_artwork(title='Солнце')
        comment = Comment(
            user_id=user.id,
            artwork_id=artwork.id,
            content='Круто!')
        db.session.add(comment)
        db.session.commit()
        repr_str = repr(comment)
        self.assertIn('Ivan', repr_str)
        self.assertIn('Солнце', repr_str)
        self.assertIn('Круто!', repr_str)
# тестирование News
class NewsTests(BaseTests):
    # создание новости
    def test_news_creation(self):
        news = News( title='Выставка 2026',
            content='Описание выставки',
            place='Москва',
            event_date=datetime(2026, 9, 18, 10, 0, 0) )
        db.session.add(news)
        db.session.commit()
        self.assertIsNotNone(news.id)
        self.assertEqual(news.title, 'Выставка 2026')
        self.assertEqual(news.place, 'Москва')
    # title и content обязательны
    def test_news_required_fields(self):
        news = News(
            title='Test',
            # content не указан
        )
        db.session.add(news)
        with self.assertRaises(IntegrityError):
            db.session.commit()
    # title обязателен
    def test_news_title_required(self):
        news = News(
            content='Test content'
            # title не указан
        )
        db.session.add(news)
        with self.assertRaises(IntegrityError):
            db.session.commit()
    # place может быть None
    def test_news_optional_place(self):
        news = News( title='Test',
            content='Content'
            # place не указан
        )
        db.session.add(news)
        db.session.commit()
        self.assertIsNone(news.place)

    # event_date может быть None
    def test_news_optional_event_date(self):
        news = News( title='Test',content='Content')
        db.session.add(news)
        db.session.commit()
        self.assertIsNone(news.event_date)
    # created_at устанавливается автоматически
    def test_news_timestamp(self):
        news = News(title='Test', content='Content')
        db.session.add(news)
        db.session.commit()
        self.assertIsNotNone(news.created_at)
    # строковое представление
    def test_news_repr(self):
        news = News(title='Fair', content='Content')
        db.session.add(news)
        db.session.commit()
        self.assertEqual(repr(news), '<News Fair>')
class IntegrationTests(BaseTests):
    #тест полного цикла
    def test_full_artwork_lifecycle(self):
        # создание пользователя и категории
        user = self._create_user(username='artist', email='artist@example.com', role=self.role_artist)
        cat = self._create_category('Масло')
        # создание тегов
        tag1 = Tag(name='пейзаж')
        tag2 = Tag(name='закат')
        db.session.add_all([tag1, tag2])
        db.session.commit()
        # создание работы
        artwork = Artwork( title='Закат',
            description='Красивый',
            image_url='/test.jpg',
            width=100,
            height=80,
            user_id=user.id,
            category_id=cat.id)
        artwork.tags.extend([tag1, tag2])
        db.session.add(artwork)
        db.session.commit()

        # лайк
        viewer = self._create_user(username='viewer', email='viewer@example.com')
        like = Like(user_id=viewer.id, artwork_id=artwork.id)
        db.session.add(like)
        #  в избранное
        fav = Favorite(user_id=viewer.id, artwork_id=artwork.id)
        db.session.add(fav)
        #  комментарий
        comment = Comment(user_id=viewer.id,
            artwork_id=artwork.id,
            content='Шедевр!')
        db.session.add(comment)
        db.session.commit()
        # проверка связей
        self.assertEqual(user.artworks.count(), 1)
        self.assertEqual(artwork.likes.count(), 1)
        self.assertEqual(artwork.favorites.count(), 1)
        self.assertEqual(artwork.comments.count(), 1)
        self.assertEqual(len(artwork.tags), 2)
        # удаление работы
        db.session.delete(artwork)
        db.session.commit()
        # проверка
        self.assertEqual(Like.query.count(), 0)
        self.assertEqual(Favorite.query.count(), 0)
        self.assertEqual(Comment.query.count(), 0)

    #проверка каскадного удаления всех данных пользователя
    def test_user_deletion_cascades_everything(self):
        user = self._create_user()
        artwork = self._create_artwork(user=user)
        # лайк, избранное, комментарий
        viewer = self._create_user(username='viewer', email='v@example.com')
        db.session.add_all([
            Like(user_id=viewer.id, artwork_id=artwork.id),
            Favorite(user_id=viewer.id, artwork_id=artwork.id),
            Comment(user_id=viewer.id, artwork_id=artwork.id, content='Test')
        ])
        db.session.commit()

        # удаление пользователя художника
        db.session.delete(user)
        db.session.commit()
        # проверка
        self.assertEqual(Artwork.query.count(), 0)
        self.assertEqual(Like.query.count(), 0)
        self.assertEqual(Favorite.query.count(), 0)
        self.assertEqual(Comment.query.count(), 0)
# запуск
if __name__ == '__main__':
    unittest.main(verbosity=2)