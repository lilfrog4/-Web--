"""
Flask сервер для онлайн-игры в крестики-нолики
Реализует REST API для игры, аутентификацию и комнаты
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import uuid
import json
import os
import hashlib
import time
from datetime import datetime

# Инициализация Flask приложения
app = Flask(__name__)
app.secret_key = 'tic_tac_toe_secret_key'  # Ключ для сессий

# In-memory хранилища (в продакшене нужно использовать Redis/БД)
games = {}          # Активные игры: {game_id: TicTacToeGame}
rooms = {}          # Игровые комнаты: {room_id: room_data}
USERS_FILE = 'users.json'           # Файл с пользователями
ACTIVE_SESSIONS = {}                # Активные сессии пользователей
game_completion_times = {}          # Время завершения игр

def load_users():
    """Загрузка пользователей из JSON файла"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Сохранение пользователей в JSON файл"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def hash_password(password):
    """Хеширование пароля с использованием SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def update_user_stats(username, result):
    """Обновление статистики пользователя после игры"""
    users = load_users()
    if username not in users:
        return
    
    # Обновляем счетчики в зависимости от результата
    if result == 'win':
        users[username]['wins'] += 1
    elif result == 'loss':
        users[username]['losses'] += 1
    elif result == 'draw':
        users[username]['draws'] += 1
    
    users[username]['games_played'] = users[username].get('games_played', 0) + 1
    save_users(users)

class TicTacToeGame:
    """
    Класс игры в крестики-нолики
    Инкапсулирует логику игры и состояние доски
    """
    def __init__(self, game_id):
        self.board = [['' for _ in range(3)] for _ in range(3)]  # 3x3 доска
        self.players = []           # Список игроков: [{'id': 0, 'username': 'name'}]
        self.current_player = 0     # Текущий игрок (0 или 1)
        self.game_id = game_id      # UUID игры
        self.winner = None          # Победитель (0, 1 или 'draw')
        self.game_over = False      # Флаг завершения игры
        
    def add_player(self, username):
        """Добавление игрока в игру"""
        if len(self.players) < 2:
            player_id = len(self.players)
            self.players.append({'id': player_id, 'username': username})
            return player_id
        return None
    
    def make_move(self, player_id, row, col):
        """
        Выполнение хода игрока
        Возвращает True если ход valid, False если invalid
        """
        # Проверка валидности хода
        if (self.winner is not None or 
            player_id != self.current_player or
            self.board[row][col] != ''):
            return False
            
        # Устанавливаем символ на доске
        symbol = 'X' if player_id == 0 else 'O'
        self.board[row][col] = symbol
        
        # Проверяем условия победы
        if self.check_winner(symbol):
            self.winner = player_id
            self.game_over = True
            self.update_stats()
        elif all(self.board[i][j] != '' for i in range(3) for j in range(3)):
            # Ничья - все клетки заполнены
            self.winner = 'draw'
            self.game_over = True
            self.update_stats()
        else:
            # Передаем ход следующему игроку
            self.current_player = 1 - self.current_player
            
        return True
    
    def check_winner(self, symbol):
        """Проверка выигрышной комбинации"""
        # Проверка строк и столбцов
        for i in range(3):
            if all(self.board[i][j] == symbol for j in range(3)) or \
               all(self.board[j][i] == symbol for j in range(3)):
                return True
        
        # Проверка диагоналей
        if all(self.board[i][i] == symbol for i in range(3)) or \
           all(self.board[i][2-i] == symbol for i in range(3)):
            return True
            
        return False
    
    def update_stats(self):
        """Обновление статистики игроков после завершения игры"""
        if self.winner == 'draw':
            for player in self.players:
                update_user_stats(player['username'], 'draw')
        else:
            for player in self.players:
                if player['id'] == self.winner:
                    update_user_stats(player['username'], 'win')
                else:
                    update_user_stats(player['username'], 'loss')

def is_user_logged_in(username):
    """Проверка активной сессии пользователя"""
    return username in ACTIVE_SESSIONS

# =============================================================================
# FLASK ROUTES - API endpoints
# =============================================================================

@app.route('/')
def index():
    """Главная страница - редирект в лобби"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Защита от множественных сессий
    if session['username'] in ACTIVE_SESSIONS:
        if ACTIVE_SESSIONS[session['username']] != session['session_id']:
            session.clear()
            return redirect(url_for('login', error='Аккаунт уже используется на другом устройстве'))
    
    return redirect(url_for('lobby'))

@app.route('/lobby')
def lobby():
    """Страница лобби с выбором комнат"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Валидация сессии
    if session['username'] in ACTIVE_SESSIONS:
        if ACTIVE_SESSIONS[session['username']] != session['session_id']:
            session.clear()
            return redirect(url_for('login', error='Сессия устарела'))
    
    return render_template('lobby.html', username=session['username'])

@app.route('/create_room', methods=['POST'])
def create_room():
    """Создание новой игровой комнаты"""
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'})
    
    username = session['username']
    room_id = str(uuid.uuid4())[:8]  # Генерируем короткий ID комнаты
    
    # Создаем комнату в состоянии ожидания
    rooms[room_id] = {
        'creator': username,
        'players': [username],
        'status': 'waiting',
        'created_at': datetime.now().isoformat()
    }
    
    # Создаем игровой инстанс
    game = TicTacToeGame(room_id)
    game.add_player(username)
    games[room_id] = game
    
    # Сохраняем в сессии
    session['game_id'] = room_id
    session['player_num'] = 0
    session['room_id'] = room_id
    
    return jsonify({
        'status': 'success',
        'room_id': room_id,
        'player_num': 0
    })

@app.route('/get_rooms')
def get_rooms():
    """Получение списка доступных комнат"""
    if 'username' not in session:
        return jsonify({'status': 'error'})
    
    # Фильтруем комнаты в состоянии ожидания
    waiting_rooms = []
    for room_id, room in rooms.items():
        if room['status'] == 'waiting' and session['username'] not in room['players']:
            waiting_rooms.append({
                'room_id': room_id,
                'creator': room['creator'],
                'players_count': len(room['players']),
                'created_at': room['created_at']
            })
    
    return jsonify({
        'status': 'success',
        'rooms': waiting_rooms
    })

@app.route('/join_room/<room_id>')
def join_room(room_id):
    """Присоединение к существующей комнате"""
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'})
    
    username = session['username']
    
    # Валидация комнаты
    if room_id not in rooms:
        return jsonify({'status': 'error', 'message': 'Комната не найдена'})
    
    room = rooms[room_id]
    
    if room['status'] != 'waiting':
        return jsonify({'status': 'error', 'message': 'Комната уже занята'})
    
    if username in room['players']:
        return jsonify({'status': 'error', 'message': 'Вы уже в этой комнате'})
    
    # Добавляем игрока в комнату
    room['players'].append(username)
    room['status'] = 'playing'
    
    # Добавляем игрока в игру
    game = games[room_id]
    player_num = game.add_player(username)
    
    # Обновляем сессию
    session['game_id'] = room_id
    session['player_num'] = player_num
    session['room_id'] = room_id
    
    return jsonify({
        'status': 'success',
        'room_id': room_id,
        'player_num': player_num
    })

@app.route('/game')
def game():
    """Страница игры"""
    if 'username' not in session or 'game_id' not in session:
        return redirect(url_for('lobby'))
    
    return render_template('game.html', username=session['username'])

@app.route('/leave_room', methods=['POST'])
def leave_room():
    """Выход из комнаты"""
    if 'username' not in session:
        return jsonify({'status': 'error'})
    
    room_id = session.get('room_id')
    if room_id in rooms:
        room = rooms[room_id]
        username = session['username']
        if username in room['players']:
            room['players'].remove(username)
            
            # Очистка пустых комнат
            if len(room['players']) == 0:
                del rooms[room_id]
                if room_id in games:
                    del games[room_id]
            elif len(room['players']) == 1:
                # Возвращаем комнату в состояние ожидания
                room['status'] = 'waiting'
    
    # Очищаем сессию
    session.pop('game_id', None)
    session.pop('player_num', None)
    session.pop('room_id', None)
    
    return jsonify({'status': 'success'})

@app.route('/move', methods=['POST'])
def make_move():
    """Обработка хода игрока"""
    if 'username' not in session or 'game_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not in game'})
    
    game_id = session.get('game_id')
    player_num = session.get('player_num')
    
    if game_id not in games:
        return jsonify({'status': 'error', 'message': 'Game not found'})
    
    # Получаем данные хода из JSON
    data = request.json
    game = games[game_id]
    success = game.make_move(player_num, data['row'], data['col'])
    
    # Запоминаем время завершения для очистки
    if game.game_over:
        game_completion_times[game_id] = time.time()
    
    return jsonify({
        'status': 'success' if success else 'error',
        'board': game.board,
        'current_player': game.current_player,
        'winner': game.winner
    })

@app.route('/game_state')
def get_game_state():
    """Получение текущего состояния игры (для polling)"""
    if 'username' not in session:
        return jsonify({'status': 'error'})
    
    game_id = session.get('game_id')
    if game_id not in games:
        return jsonify({'status': 'error', 'message': 'Game not found'})
    
    game = games[game_id]
    
    # Проверяем, что пользователь действительно в этой игре
    user_in_game = any(player['username'] == session['username'] for player in game.players)
    if not user_in_game:
        return jsonify({'status': 'error', 'message': 'Not in this game'})
    
    # Находим номер игрока в текущей сессии
    player_num = None
    for i, player in enumerate(game.players):
        if player['username'] == session['username']:
            player_num = i
            break
    
    # Логирование для дебага
    print(f"Game state request from {session['username']}: "
          f"player_num={player_num}, current_player={game.current_player}, "
          f"players={[p['username'] for p in game.players]}")
    
    # Очистка завершенных игр с задержкой (чтобы оба игрока увидели результат)
    if game.game_over and game_id in game_completion_times:
        if time.time() - game_completion_times[game_id] > 5:  # 5 секунд задержки
            room_id = game_id
            if room_id in rooms:
                del rooms[room_id]
            if game_id in games:
                del games[game_id]
            if game_id in game_completion_times:
                del game_completion_times[game_id]
    
    # Формируем ответ с заголовками против кэширования
    response = jsonify({
        'status': 'success',
        'game_id': game_id,
        'board': game.board,
        'current_player': game.current_player,
        'winner': game.winner,
        'player_num': player_num,
        'players': [p['username'] for p in game.players]
    })
    
    # Заголовки для предотвращения кэширования
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    error = request.args.get('error')
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        users = load_users()
        
        # Проверка учетных данных
        if username in users and users[username]['password'] == hash_password(password):
            # Защита от множественного входа
            if is_user_logged_in(username):
                return render_template('login.html', error='Аккаунт уже используется на другом устройстве')
            
            # Создаем новую сессию
            session_id = str(uuid.uuid4())
            session['username'] = username
            session['session_id'] = session_id
            session['player_id'] = str(uuid.uuid4())
            ACTIVE_SESSIONS[username] = session_id
            
            return redirect(url_for('lobby'))
        return render_template('login.html', error='Неверный логин или пароль')
    
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Валидация входных данных
        if not username or len(username) < 3:
            return render_template('register.html', error='Логин должен быть не менее 3 символов')
        
        if not password or len(password) < 4:
            return render_template('register.html', error='Пароль должен быть не менее 4 символов')
        
        users = load_users()
        if username in users:
            return render_template('register.html', error='Логин уже занят')
        
        # Создаем нового пользователя
        users[username] = {
            'password': hash_password(password),
            'wins': 0,
            'losses': 0,
            'draws': 0,
            'games_played': 0,
            'registered_at': datetime.now().isoformat()
        }
        save_users(users)
        
        # Автоматический вход после регистрации
        session_id = str(uuid.uuid4())
        session['username'] = username
        session['session_id'] = session_id
        session['player_id'] = str(uuid.uuid4())
        ACTIVE_SESSIONS[username] = session_id
        
        return redirect(url_for('lobby'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
    if 'username' in session:
        if session['username'] in ACTIVE_SESSIONS:
            del ACTIVE_SESSIONS[session['username']]
    session.clear()
    return redirect(url_for('login'))

@app.route('/stats')
def stats():
    """Страница статистики и рейтинга"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Валидация сессии
    if session['username'] in ACTIVE_SESSIONS:
        if ACTIVE_SESSIONS[session['username']] != session['session_id']:
            session.clear()
            return redirect(url_for('login', error='Сессия устарела'))
    
    users = load_users()
    current_user = session['username']
    user_stats = users.get(current_user, {})
    
    # Формируем топ игроков
    top_players = []
    for username, stats_data in users.items():
        if stats_data.get('games_played', 0) > 0:
            # Расчет процента побед
            win_rate = (stats_data.get('wins', 0) / stats_data.get('games_played', 0)) * 100
            top_players.append({
                'username': username,
                'wins': stats_data.get('wins', 0),
                'losses': stats_data.get('losses', 0),
                'draws': stats_data.get('draws', 0),
                'games_played': stats_data.get('games_played', 0),
                'win_rate': round(win_rate, 1)  # Округление до 1 знака
            })
    
    # Сортировка по количеству побед (от большего к меньшему)
    top_players.sort(key=lambda x: x['wins'], reverse=True)
    
    return render_template('stats.html', 
                         stats=user_stats, 
                         username=current_user,
                         top_players=top_players[:10])  # Топ-10 игроков

if __name__ == '__main__':
    # Запуск development сервера
    app.run(host='0.0.0.0', port=5000, debug=True)