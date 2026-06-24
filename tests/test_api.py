import unittest
import json
from app import create_app
from app.db_create import db
from app.models import User, Role, Artwork, Category, Like


class BaseAPITest(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        # test_client имитирует браузер
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        role_viewer = Role(name='Viewer')
        role_artist = Role(name='Artist')
        db.session.add_all([role_viewer, role_artist])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
#регистрация
    def _register_user(self, username, email, password, role_name='Artist'):
        return self.client.post('/auth/register', json={'username': username,
            'email': email,
            'password': password,
            'confirm_password': password,
            'role': role_name
        })
#для возврата токена
    def _login_user(self, email, password):
        resp = self.client.post('/auth/login', json={
            'email': email,
            'password': password
        })
        data = json.loads(resp.data)
        return data.get('access_token')

    def _get_headers(self, token):
        # заголовки с токеном
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }


class AuthAPITests(BaseAPITest):
    #успешная регистрация
    def test_register_success(self):
        resp = self._register_user('artist_test', 'artist@test.com', 'password123', 'Artist')
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertIn('access_token', data)
        self.assertIn('message', data)

    def test_register_duplicate_email(self):
        self._register_user('user1', 'dup@test.com', 'pass123456')
        resp = self._register_user('user2', 'dup@test.com', 'pass123456')
        self.assertEqual(resp.status_code, 400)  # или 409, зависит от вашей логики
    #успешный вход
    def test_login_success(self):
        self._register_user('login_user', 'login@test.com', 'password123')
        token = self._login_user('login@test.com', 'password123')
        self.assertIsNotNone(token)
    # вход с неверным паролем
    def test_login_wrong_password(self):
        self._register_user('login_user', 'login@test.com', 'password123')
        resp = self.client.post('/auth/login', json={'email': 'login@test.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(resp.status_code, 401)


class ArtworkAPITests(BaseAPITest):
    def setUp(self):
        super().setUp()
        # получение токена художника
        self._register_user('artist_api', 'artist@api.com', 'password123', 'Artist')
        self.token = self._login_user('artist@api.com', 'password123')
        cat = Category(name='Масло')
        db.session.add(cat)
        db.session.commit()
        self.category_id = cat.id
# создание работы
    def test_create_artwork_success(self):
        headers = self._get_headers(self.token)
        data = {
            'title': 'Test Art',
            'description': 'Desc',
            'image_url': 'http://test.com/image.jpg',
            'category_id': self.category_id,
            'width': 100,
            'height': 100,
            'tags': ['test']
        }
        resp = self.client.post('/artworks', json=data, headers=headers)
        self.assertEqual(resp.status_code, 201)

        # проверка работы в БД
        artwork = Artwork.query.filter_by(title='Test Art').first()
        self.assertIsNotNone(artwork)
#создание работы без токена
    def test_create_artwork_unauthorized(self):
        data = {'title': 'Fail'}
        resp = self.client.post('/artworks', json=data)
        self.assertEqual(resp.status_code, 401)

    def test_get_artworks_list(self):
        self.test_create_artwork_success()

        resp = self.client.get('/artworks')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('items', data)
        self.assertGreaterEqual(len(data['items']), 1)


class InteractionAPITests(BaseAPITest):
    def setUp(self):
        super().setUp()
        # создание художника и работы
        self._register_user('artist_int', 'artist@int.com', 'password123', 'Artist')
        artist_token = self._login_user('artist@int.com', 'password123')

        cat = Category(name='Акварель')
        db.session.add(cat)
        db.session.commit()

        headers = self._get_headers(artist_token)
        art_data = {'title': 'Like Me',
            'image_url': 'http://test.com/like.jpg',
            'category_id': cat.id,
            'width': 10,
            'height': 10}
        resp = self.client.post('/artworks', json=art_data, headers=headers)
        self.artwork_id = json.loads(resp.data)['artwork_id']
        # создание зрителя для лайков

        self._register_user('viewer_int', 'viewer@int.com', 'password123', 'Viewer')
        self.viewer_token = self._login_user('viewer@int.com', 'password123')

    # постановка лайка
    def test_like_artwork(self):
        headers = self._get_headers(self.viewer_token)
        resp = self.client.post(f'/likes/{self.artwork_id}', headers=headers)
        self.assertEqual(resp.status_code, 201)

        # Проверка БД
        like = Like.query.filter_by(artwork_id=self.artwork_id).first()
        self.assertIsNotNone(like)
    #модерация комментариев
    def test_add_comment_bad_word(self):
        headers = self._get_headers(self.viewer_token)
        resp = self.client.post(f'/comments/{self.artwork_id}', json={
            'content': 'Ты дурак'  # слово из bad_words.py
        }, headers=headers)
        self.assertEqual(resp.status_code, 400)
if __name__ == '__main__':
    unittest.main(verbosity=2)