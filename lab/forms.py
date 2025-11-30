from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, PasswordField, SelectField
from wtforms.validators import DataRequired, Length, ValidationError, EqualTo
import re

def email_validator(form, field):
    email = field.data
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise ValidationError('Введите корректный email адрес')

class FeedbackForm(FlaskForm):
    name = StringField('Имя', validators=[
        DataRequired(message='Поле обязательно для заполнения'),
        Length(min=2, max=50, message='Имя должно быть от 2 до 50 символов')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Поле обязательно для заполнения'),
        email_validator
    ])
    message = TextAreaField('Сообщение', validators=[
        DataRequired(message='Поле обязательно для заполнения'),
        Length(min=10, max=500, message='Сообщение должно быть от 10 до 500 символов')
    ])
    submit = SubmitField('Отправить')

class ArticleForm(FlaskForm):
    title = StringField('Заголовок', validators=[
        DataRequired(message='Введите заголовок статьи'),
        Length(min=5, max=200, message='Заголовок должен быть от 5 до 200 символов')
    ])
    text = TextAreaField('Текст статьи', validators=[
        DataRequired(message='Введите текст статьи'),
        Length(min=10, message='Текст статьи должен быть не менее 10 символов')
    ])
    category = SelectField('Категория', choices=[
        ('general', 'Общее'),
        ('politics', 'Политика'),
        ('technology', 'Технологии'),
        ('sports', 'Спорт'),
        ('culture', 'Культура')
    ], validators=[DataRequired()])
    submit = SubmitField('Создать статью')

class CommentForm(FlaskForm):
    # Убрали author_name - будет браться из текущего пользователя
    text = TextAreaField('Комментарий', validators=[
        DataRequired(message='Введите текст комментария'),
        Length(min=5, max=500, message='Комментарий должен быть от 5 до 500 символов')
    ])
    submit = SubmitField('Добавить комментарий')

class RegistrationForm(FlaskForm):
    name = StringField('Имя', validators=[
        DataRequired(message='Введите ваше имя'),
        Length(min=2, max=100, message='Имя должно быть от 2 до 100 символов')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Введите email'),
        email_validator
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Введите пароль'),
        Length(min=6, message='Пароль должен быть не менее 6 символов')
    ])
    confirm_password = PasswordField('Подтвердите пароль', validators=[
        DataRequired(message='Подтвердите пароль'),
        EqualTo('password', message='Пароли должны совпадать')
    ])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message='Введите email'),
        email_validator
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Введите пароль')
    ])
    submit = SubmitField('Войти')