# api_forms.py - Валидация для API
class ArticleApiForm:
    @staticmethod
    def validate(data):
        errors = {}
        
        # Валидация title
        title = data.get('title', '').strip()
        if not title:
            errors['title'] = ['Заголовок обязателен']
        elif len(title) < 5 or len(title) > 200:
            errors['title'] = ['Заголовок должен быть от 5 до 200 символов']
        
        # Валидация text
        text = data.get('text', '').strip()
        if not text:
            errors['text'] = ['Текст статьи обязателен']
        elif len(text) < 10:
            errors['text'] = ['Текст статьи должен быть не менее 10 символов']
        
        # Валидация category
        category = data.get('category', 'general')
        valid_categories = ['general', 'politics', 'technology', 'sports', 'culture']
        if category not in valid_categories:
            errors['category'] = [f'Категория должна быть одной из: {", ".join(valid_categories)}']
        
        # Валидация user_id
        user_id = data.get('user_id')
        if not user_id:
            errors['user_id'] = ['user_id обязателен']
        elif not isinstance(user_id, int):
            errors['user_id'] = ['user_id должен быть числом']
        
        return len(errors) == 0, errors

class CommentApiForm:
    @staticmethod
    def validate(data):
        errors = {}
        
        # Валидация text
        text = data.get('text', '').strip()
        if not text:
            errors['text'] = ['Текст комментария обязателен']
        elif len(text) < 5 or len(text) > 500:
            errors['text'] = ['Комментарий должен быть от 5 до 500 символов']
        
        # Валидация article_id
        article_id = data.get('article_id')
        if not article_id:
            errors['article_id'] = ['article_id обязателен']
        elif not isinstance(article_id, int):
            errors['article_id'] = ['article_id должен быть числом']
        
        # author_name больше не нужен - берется из текущего пользователя
        
        return len(errors) == 0, errors