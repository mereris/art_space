from datetime  import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role %r>' % self.name


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)

    bio = db.Column(db.Text)
    avatar_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default = datetime.now(timezone.utc), nullable=False)

    role_id = (db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False))
    artworks = db.relationship('Artwork', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    favorites = db.relationship('Favorite', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def password(self):
        raise AttributeError('Пароль недоступен к прочтению')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User %r>' % self.username

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    artworks = db.relationship('Artwork', backref='category', lazy='dynamic')
    def __repr__(self):
        return f'<Category {self.name}>'
class Artwork(db.Model):
    __tablename__ = 'artworks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default = datetime.now(timezone.utc))

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)

    likes = db.relationship('Like', backref='artwork', lazy='dynamic', cascade='all, delete-orphan')
    favorites = db.relationship('Favorite', backref='artwork', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='artwork', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Artwork {self.title}; Author {self.author.username}>'

class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    artwork_id = db.Column(db.Integer, db.ForeignKey('artworks.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default = datetime.now(timezone.utc), nullable=False)
    #ограничение на одну работу - от 1 пользователя только 1 лайк
    table_args =  (db.UniqueConstraint('user_id', 'artwork_id', name='unique_like'),)

    def __repr__(self):
        return f'<Like by {self.user.username}; Artwork {self.artwork.title}>'
class Favorite(db.Model):
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    artwork_id = db.Column(db.Integer, db.ForeignKey('artworks.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    # ограничение на добавление работы в единственном экземпляре
    table_args = (db.UniqueConstraint('user_id', 'artwork_id', name='favorite_by_once'),)


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    artwork_id = db.Column(db.Integer, db.ForeignKey('artworks.id', ondelete='CASCADE'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f'<User: {self.user.username} | Comment on Artwork {self.artwork.title}: {self.content}>'


class News(db.Model):
    __tablename__ = 'news'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    event_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)

    def __repr__ (self):
        return f'<News {self.title}>'