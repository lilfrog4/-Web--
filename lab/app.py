from flask import Flask, render_template, url_for, request, redirect, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import date
from forms import FeedbackForm, ArticleForm, CommentForm, RegistrationForm, LoginForm
from models import db, User, Article, Comment

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///news_blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Импортируем формы API
try:
    from api_forms import ArticleApiForm, CommentApiForm
except ImportError:
    class ArticleApiForm:
        @staticmethod
        def validate(data):
            errors = {}
            title = data.get('title', '').strip()
            if not title:
                errors['title'] = ['Заголовок обязателен']
            text = data.get('text', '').strip()
            if not text:
                errors['text'] = ['Текст статьи обязателен']
            return len(errors) == 0, errors

    class CommentApiForm:
        @staticmethod
        def validate(data):
            errors = {}
            text = data.get('text', '').strip()
            if not text:
                errors['text'] = ['Текст комментария обязателен']
            return len(errors) == 0, errors

# Инициализация расширений
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Контекстный процессор
@app.context_processor
def inject_current_date():
    return {'current_date': date.today()}

# ============================================================================
# ВЕБ-МАРШРУТЫ
# ============================================================================

@app.route('/')
def index():
    # На главной всегда показываем сначала новые
    articles = Article.query.order_by(Article.created_date.desc()).limit(3).all()
    return render_template('index.html', articles=articles)

@app.route('/articles')
def articles():
    category = request.args.get('category')
    sort = request.args.get('sort', 'newest')  # newest или oldest
    
    # Базовый запрос
    query = Article.query
    
    # Фильтрация по категории
    if category:
        query = query.filter_by(category=category)
    
    # Сортировка по времени
    if sort == 'oldest':
        articles_list = query.order_by(Article.created_date.asc()).all()
    else:  # newest по умолчанию
        articles_list = query.order_by(Article.created_date.desc()).all()
    
    # Получаем русские названия категорий для отображения
    category_names = {
        'general': 'Общее',
        'politics': 'Политика', 
        'technology': 'Технологии',
        'sports': 'Спорт',
        'culture': 'Культура'
    }
    
    current_category_name = category_names.get(category, category)
    
    return render_template('articles.html', 
                         articles=articles_list, 
                         current_category=category,
                         current_category_name=current_category_name,
                         current_sort=sort)

# НОВЫЙ МАРШРУТ: Страница всех комментариев
@app.route('/comments')
def all_comments():
    # Получаем параметры
    article_id = request.args.get('article_id')
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Количество комментариев на странице
    
    # Базовый запрос
    if article_id:
        query = Comment.query.filter_by(article_id=article_id)
        article = Article.query.get(article_id)
        title = f"Комментарии к статье: {article.title}" if article else "Комментарии"
    else:
        query = Comment.query
        title = "Все комментарии"
        article = None
    
    # Сортировка по дате (новые сначала)
    comments = query.order_by(Comment.date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('all_comments.html', 
                         comments=comments,
                         title=title,
                         article=article)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Пользователь с таким email уже существует', 'danger')
            return render_template('register.html', form=form)
        
        user = User(name=form.name.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f'Добро пожаловать, {user.name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Неверный email или пароль', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

@app.route('/create-article', methods=['GET', 'POST'])
@login_required
def create_article():
    form = ArticleForm()
    if form.validate_on_submit():
        article = Article(
            title=form.title.data,
            text=form.text.data,
            category=form.category.data,
            user_id=current_user.id
        )
        db.session.add(article)
        db.session.commit()
        flash('Статья успешно создана!', 'success')
        return redirect(url_for('articles'))
    return render_template('create_article.html', form=form)

@app.route('/edit-article/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_article(id):
    article = Article.query.get_or_404(id)
    if article.author != current_user:
        flash('Вы можете редактировать только свои статьи', 'danger')
        return redirect(url_for('articles'))
    
    form = ArticleForm()
    if form.validate_on_submit():
        article.title = form.title.data
        article.text = form.text.data
        article.category = form.category.data
        db.session.commit()
        flash('Статья успешно обновлена!', 'success')
        return redirect(url_for('news_article', id=article.id))
    
    form.title.data = article.title
    form.text.data = article.text
    form.category.data = article.category
    return render_template('edit_article.html', form=form, article=article)

@app.route('/delete-article/<int:id>')
@login_required
def delete_article(id):
    article = Article.query.get_or_404(id)
    if article.author != current_user:
        flash('Вы можете удалять только свои статьи', 'danger')
        return redirect(url_for('articles'))
    
    db.session.delete(article)
    db.session.commit()
    flash('Статья успешно удалена!', 'success')
    return redirect(url_for('articles'))

@app.route('/news/<int:id>', methods=['GET', 'POST'])
def news_article(id):
    article = Article.query.get_or_404(id)
    form = CommentForm()
    
    if form.validate_on_submit():
        # Проверяем, авторизован ли пользователь
        if not current_user.is_authenticated:
            flash('Для добавления комментария необходимо войти в систему', 'warning')
            return redirect(url_for('login'))
        
        # Создаем комментарий с именем текущего пользователя
        comment = Comment(
            text=form.text.data,
            author_name=current_user.name,  # Берем имя из текущего пользователя
            article_id=article.id,
            user_id=current_user.id  # Сохраняем ID пользователя
        )
        
        db.session.add(comment)
        db.session.commit()
        
        flash('Комментарий добавлен!', 'success')
        return redirect(url_for('news_article', id=article.id))
    
    comments = Comment.query.filter_by(article_id=article.id).order_by(Comment.date.desc()).limit(10).all()
    total_comments = Comment.query.filter_by(article_id=article.id).count()
    
    return render_template('article.html', 
                         article=article, 
                         form=form, 
                         comments=comments,
                         total_comments=total_comments)

# МАРШРУТ: Удаление комментария
@app.route('/delete-comment/<int:comment_id>')
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    article_id = comment.article_id
    
    # Проверяем, является ли пользователь владельцем комментария
    if not comment.is_owner(current_user):
        flash('Вы можете удалять только свои комментарии', 'danger')
        return redirect(url_for('news_article', id=article_id))
    
    db.session.delete(comment)
    db.session.commit()
    flash('Комментарий успешно удален!', 'success')
    return redirect(url_for('news_article', id=article_id))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        message = form.message.data
        return render_template('feedback.html', form=form, submitted=True, 
                             name=name, email=email, message=message)
    return render_template('feedback.html', form=form, submitted=False)

# ============================================================================
# API ROUTES (остаются без изменений)
# ============================================================================

# [Здесь все API маршруты остаются без изменений...]

# A. Базовые эндпоинты для статей
@app.route('/api/articles', methods=['GET'])
def api_get_articles():
    """A.a. GET /api/articles — список всех статей с фильтрацией и сортировкой"""
    try:
        # Получаем параметры
        category = request.args.get('category')
        order = request.args.get('order', 'desc')  # desc или asc
        
        # Базовый запрос
        query = Article.query
        
        # Фильтрация по категории
        if category:
            query = query.filter_by(category=category)
        
        # Сортировка по дате
        if order == 'asc':
            articles = query.order_by(Article.created_date.asc()).all()
        else:
            articles = query.order_by(Article.created_date.desc()).all()
        
        return jsonify({
            'success': True,
            'articles': [article.to_dict() for article in articles],
            'count': len(articles),
            'filters': {
                'category': category,
                'order': order
            }
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/articles/<int:article_id>', methods=['GET'])
def api_get_article(article_id):
    """A.b. GET /api/articles/<id> — статья по ID"""
    try:
        article = Article.query.get_or_404(article_id)
        return jsonify({
            'success': True,
            'article': article.to_dict()
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Статья не найдена'
        }), 404

# B. CRUD через API для статей
@app.route('/api/articles', methods=['POST'])
def api_create_article():
    """B.a. POST /api/articles — создать статью"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        # Валидация
        is_valid, errors = ArticleApiForm.validate(data)
        if not is_valid:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        # Проверка существования пользователя
        user = User.query.get(data['user_id'])
        if not user:
            return jsonify({
                'success': False,
                'error': 'Пользователь не найден'
            }), 404
        
        # Создание статьи
        article = Article(
            title=data['title'],
            text=data['text'],
            category=data.get('category', 'general'),
            user_id=data['user_id']
        )
        
        db.session.add(article)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'article': article.to_dict(),
            'message': 'Статья успешно создана'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/articles/<int:article_id>', methods=['PUT'])
def api_update_article(article_id):
    """B.b. PUT /api/articles/<id> — обновить статью"""
    try:
        article = Article.query.get_or_404(article_id)
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        # Валидация
        is_valid, errors = ArticleApiForm.validate(data)
        if not is_valid:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        # Обновление статьи
        article.title = data['title']
        article.text = data['text']
        article.category = data.get('category', article.category)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'article': article.to_dict(),
            'message': 'Статья успешно обновлена'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/articles/<int:article_id>', methods=['DELETE'])
def api_delete_article(article_id):
    """B.c. DELETE /api/articles/<id> — удалить статью"""
    try:
        article = Article.query.get_or_404(article_id)
        
        db.session.delete(article)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Статья успешно удалена'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# C. Фильтрация и сортировка
@app.route('/api/articles/category/<string:category>', methods=['GET'])
def api_get_articles_by_category(category):
    """C.a. GET /api/articles/category/<category> — фильтр по категории"""
    try:
        valid_categories = ['general', 'politics', 'technology', 'sports', 'culture']
        if category not in valid_categories:
            return jsonify({
                'success': False,
                'error': f'Недопустимая категория. Допустимые: {", ".join(valid_categories)}'
            }), 400
        
        # Параметр сортировки
        order = request.args.get('order', 'desc')
        
        if order == 'asc':
            articles = Article.query.filter_by(category=category).order_by(Article.created_date.asc()).all()
        else:
            articles = Article.query.filter_by(category=category).order_by(Article.created_date.desc()).all()
        
        return jsonify({
            'success': True,
            'articles': [article.to_dict() for article in articles],
            'count': len(articles),
            'category': category,
            'order': order
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/articles/sort/date', methods=['GET'])
def api_get_articles_sorted_by_date():
    """C.b. GET /api/articles/sort/date — сортировка по дате"""
    try:
        # Параметр для направления сортировки
        order = request.args.get('order', 'desc')  # desc или asc
        
        if order == 'asc':
            articles = Article.query.order_by(Article.created_date.asc()).all()
        else:
            articles = Article.query.order_by(Article.created_date.desc()).all()
        
        return jsonify({
            'success': True,
            'articles': [article.to_dict() for article in articles],
            'count': len(articles),
            'order': order,
            'description': 'Сортировка по дате создания статей'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# D. CRUD для комментариев
@app.route('/api/comments', methods=['GET'])
def api_get_comments():
    """D.a. GET /api/comments — список всех комментариев"""
    try:
        # Фильтрация по статье
        article_id = request.args.get('article_id')
        if article_id:
            comments = Comment.query.filter_by(article_id=article_id).order_by(Comment.date.desc()).all()
        else:
            comments = Comment.query.order_by(Comment.date.desc()).all()
        
        return jsonify({
            'success': True,
            'comments': [comment.to_dict() for comment in comments],
            'count': len(comments)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/comments/<int:comment_id>', methods=['GET'])
def api_get_comment(comment_id):
    """D.b. GET /api/comments/<id> — комментарий по ID"""
    try:
        comment = Comment.query.get_or_404(comment_id)
        return jsonify({
            'success': True,
            'comment': comment.to_dict()
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Комментарий не найден'
        }), 404

@app.route('/api/comments', methods=['POST'])
def api_create_comment():
    """D.c. POST /api/comments — создать комментарий"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        # Валидация
        is_valid, errors = CommentApiForm.validate(data)
        if not is_valid:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        # Проверка существования статьи
        article = Article.query.get(data['article_id'])
        if not article:
            return jsonify({
                'success': False,
                'error': 'Статья не найдена'
            }), 404
        
        # Создание комментария
        comment = Comment(
            text=data['text'],
            author_name=data.get('author_name', 'Аноним'),
            article_id=data['article_id']
        )
        
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'comment': comment.to_dict(),
            'message': 'Комментарий успешно создан'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/comments/<int:comment_id>', methods=['PUT'])
def api_update_comment(comment_id):
    """D.d. PUT /api/comments/<id> — обновить комментарий"""
    try:
        comment = Comment.query.get_or_404(comment_id)
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        # Валидация
        is_valid, errors = CommentApiForm.validate(data)
        if not is_valid:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        # Обновление комментария
        comment.text = data['text']
        if 'author_name' in data:
            comment.author_name = data['author_name']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'comment': comment.to_dict(),
            'message': 'Комментарий успешно обновлен'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/comments/<int:comment_id>', methods=['DELETE'])
def api_delete_comment(comment_id):
    """D.e. DELETE /api/comments/<id> — удалить комментарий"""
    try:
        comment = Comment.query.get_or_404(comment_id)
        
        db.session.delete(comment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Комментарий успешно удален'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# ============================================================================

def init_db():
    with app.app_context():
        db.create_all()
        
        if not User.query.filter_by(email='admin@example.com').first():
            user = User(name='Admin', email='admin@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)