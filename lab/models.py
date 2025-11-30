from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    hashed_password = db.Column(db.String(200), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    articles = db.relationship('Article', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    
    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'created_date': self.created_date.isoformat()
        }

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general')
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='article', lazy=True, cascade='all, delete-orphan', order_by='Comment.date.desc()')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'text': self.text,
            'category': self.category,
            'created_date': self.created_date.isoformat(),
            'user_id': self.user_id,
            'author_name': self.author.name,
            'comments_count': len(self.comments)
        }
    
    @classmethod
    def get_all_with_filters(cls, category=None, sort_by='date', order='desc'):
        """Получить статьи с фильтрацией и сортировкой"""
        query = cls.query
        
        # Фильтрация по категории
        if category:
            query = query.filter_by(category=category)
        
        # Сортировка
        if sort_by == 'date':
            if order == 'asc':
                query = query.order_by(cls.created_date.asc())
            else:
                query = query.order_by(cls.created_date.desc())
        
        return query.all()
    
    @classmethod
    def get_sorted_by_date(cls, order='desc'):
        """Получить статьи отсортированные по дате"""
        if order == 'asc':
            return cls.query.order_by(cls.created_date.asc()).all()
        else:
            return cls.query.order_by(cls.created_date.desc()).all()
    
    @classmethod
    def get_by_category_sorted(cls, category, order='desc'):
        """Получить статьи категории отсортированные по дате"""
        if order == 'asc':
            return cls.query.filter_by(category=category).order_by(cls.created_date.asc()).all()
        else:
            return cls.query.filter_by(category=category).order_by(cls.created_date.desc()).all()

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    author_name = db.Column(db.String(100), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'date': self.date.isoformat(),
            'author_name': self.author_name,
            'article_id': self.article_id,
            'user_id': self.user_id,
            'article_title': self.article.title if self.article else None
        }
    
    def is_owner(self, user):
        """Проверяет, является ли пользователь владельцем комментария"""
        return self.user_id == user.id