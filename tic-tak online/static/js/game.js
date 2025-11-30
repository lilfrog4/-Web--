/**
 * Клиентский модуль для игры в крестики-нолики
 * Реализует взаимодействие с сервером через REST API
 * Использует polling для обновления состояния игры
 */
const game = {
    // Состояние игры
    gameId: null,           // ID текущей игры
    playerNum: null,        // Номер игрока (0 или 1)
    currentPlayer: 0,       // Текущий активный игрок
    pollInterval: null,     // Интервал для polling
    lastBoardState: null,   // Последнее состояние доски для сравнения

    /**
     * Инициализация игры
     * Загружает состояние и запускает polling
     */
    init() {
        console.log('🚀 Initializing game...');
        this.loadGameState();
    },

    /**
     * Загрузка текущего состояния игры с сервера
     * Определяет тип игры (онлайн) и настраивает интерфейс
     */
    loadGameState() {
        console.log('📡 Loading game state...');
        fetch('/game_state')
            .then(r => {
                if (!r.ok) throw new Error('Network error');
                return r.json();
            })
            .then(data => {
                console.log('🎮 Game state response:', data);
                if (data.status === 'success') {
                    // Сохраняем данные игры
                    this.gameId = data.game_id;
                    this.playerNum = data.player_num;
                    this.currentPlayer = data.current_player;
                    this.lastBoardState = JSON.stringify(data.board);
                    
                    console.log('👤 Player info:', {
                        playerNum: this.playerNum,
                        currentPlayer: this.currentPlayer,
                        isMyTurn: this.currentPlayer === this.playerNum,
                        gameId: this.gameId
                    });
                    
                    // Инициализируем интерфейс
                    this.createBoard();
                    this.updateGameState(data);
                    this.startPolling();
                } else {
                    console.log('❌ No active game, redirecting to lobby. Error:', data.message);
                    this.redirectToLobby();
                }
            })
            .catch(error => {
                console.error('💥 Error loading game state:', error);
                this.redirectToLobby();
            });
    },

    /**
     * Создание игрового поля 3x3
     * Динамически генерирует ячейки и назначает обработчики
     */
    createBoard() {
        const board = document.getElementById('board');
        board.innerHTML = '';
        
        // Создаем 9 ячеек (3x3)
        for (let i = 0; i < 3; i++) {
            for (let j = 0; j < 3; j++) {
                const cell = document.createElement('div');
                cell.className = 'cell';
                cell.dataset.row = i;      // Сохраняем координаты
                cell.dataset.col = j;
                cell.onclick = () => this.makeMove(i, j);  // Обработчик клика
                board.appendChild(cell);
            }
        }
        console.log('🎲 Board created for player:', this.playerNum);
    },

    /**
     * Обработка хода игрока
     * @param {number} row - Строка (0-2)
     * @param {number} col - Колонка (0-2)
     */
    makeMove(row, col) {
        const isMyTurn = this.currentPlayer === this.playerNum;
        console.log('🎯 Attempting move:', { 
            row, col, 
            playerNum: this.playerNum, 
            currentPlayer: this.currentPlayer,
            isMyTurn: isMyTurn
        });
        
        // Проверяем, что ход текущего игрока
        if (!isMyTurn) {
            console.log('⏳ Not your turn!');
            this.updateStatus('Сейчас не ваш ход!');
            return;
        }
        
        // Блокируем доску на время запроса
        const board = document.getElementById('board');
        board.classList.add('loading');
        
        // Отправляем ход на сервер
        fetch('/move', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({row, col})
        })
        .then(r => {
            if (!r.ok) throw new Error('Network error');
            return r.json();
        })
        .then(state => {
            board.classList.remove('loading');
            console.log('✅ Move response:', state);
            if (state.status === 'success') {
                this.updateGameState(state);
                // Принудительное обновление после хода
                setTimeout(() => this.forceUpdate(), 500);
            } else {
                this.updateStatus('Ошибка хода: ' + (state.message || 'Неизвестная ошибка'));
            }
        })
        .catch(error => {
            console.error('💥 Move error:', error);
            board.classList.remove('loading');
            this.updateStatus('Ошибка соединения');
        });
    },

    /**
     * Обновление интерфейса на основе состояния игры
     * @param {Object} state - Состояние игры с сервера
     */
    updateGameState(state) {
        if (state.status !== 'success') {
            console.log('❌ Invalid game state, redirecting...');
            this.redirectToLobby();
            return;
        }
        
        // Сравниваем состояние доски для оптимизации
        const currentBoardState = JSON.stringify(state.board);
        const boardChanged = this.lastBoardState !== currentBoardState;
        this.lastBoardState = currentBoardState;
        
        console.log('🔄 Updating game state:', {
            currentPlayer: state.current_player,
            playerNum: this.playerNum,
            isMyTurn: state.current_player === this.playerNum,
            boardChanged: boardChanged,
            players: state.players
        });
        
        // Обновляем доску только при изменениях
        if (boardChanged) {
            const board = document.getElementById('board');
            const cells = board.getElementsByClassName('cell');
            
            // Проходим по всем ячейкам доски
            for (let i = 0; i < 3; i++) {
                for (let j = 0; j < 3; j++) {
                    const cell = cells[i * 3 + j];
                    const cellValue = state.board[i][j] || '';
                    cell.textContent = cellValue;
                    cell.className = 'cell';  // Сбрасываем классы
                    
                    // Добавляем классы для стилизации
                    if (cellValue === 'X') {
                        cell.classList.add('x');  // Синие крестики
                    } else if (cellValue === 'O') {
                        cell.classList.add('o');  // Белые нолики
                    }
                }
            }
            console.log('🎲 Board updated');
        }
        
        // Обновляем имена игроков
        if (state.players && state.players.length === 2) {
            document.getElementById('playerXName').textContent = state.players[0];
            document.getElementById('playerOName').textContent = state.players[1];
        }
        
        // Обновляем состояние
        this.currentPlayer = state.current_player;
        this.updateStatus();
        this.updatePlayerBadges();
        
        // Проверяем завершение игры
        this.checkGameEnd(state);
    },

    /**
     * Проверка и отображение результата игры
     * @param {Object} state - Состояние игры
     */
    checkGameEnd(state) {
        const resultDiv = document.getElementById('gameResult');
        resultDiv.innerHTML = '';
        
        if (state.winner !== null && state.winner !== undefined) {
            if (state.winner === 'draw') {
                resultDiv.innerHTML = '<div class="draw-message">🤝 Ничья!</div>';
            } else {
                const winnerSymbol = state.winner === 0 ? 'X' : 'O';
                const winnerName = state.players ? state.players[state.winner] : `Игрок ${winnerSymbol}`;
                resultDiv.innerHTML = `<div class="winner-message">🎉 Победил ${winnerName}!</div>`;
                
                // Подсвечиваем выигрышную комбинацию
                this.highlightWinningCombination(state.board, winnerSymbol);
            }
            
            console.log('🏁 Game ended, stopping polling');
            this.stopPolling();
            // Возвращаем в лобби через 3 секунды
            setTimeout(() => {
                this.returnToLobby();
            }, 3000);
        }
    },

    /**
     * Подсветка выигрышной комбинации
     * @param {Array} board - Состояние доски
     * @param {string} symbol - Символ победителя
     */
    highlightWinningCombination(board, symbol) {
        // Проверка строк
        for (let i = 0; i < 3; i++) {
            if (board[i][0] === symbol && board[i][1] === symbol && board[i][2] === symbol) {
                for (let j = 0; j < 3; j++) {
                    const cell = document.querySelector(`.cell[data-row="${i}"][data-col="${j}"]`);
                    if (cell) cell.classList.add('winning');
                }
                return;
            }
        }
        
        // Проверка столбцов
        for (let j = 0; j < 3; j++) {
            if (board[0][j] === symbol && board[1][j] === symbol && board[2][j] === symbol) {
                for (let i = 0; i < 3; i++) {
                    const cell = document.querySelector(`.cell[data-row="${i}"][data-col="${j}"]`);
                    if (cell) cell.classList.add('winning');
                }
                return;
            }
        }
        
        // Проверка главной диагонали
        if (board[0][0] === symbol && board[1][1] === symbol && board[2][2] === symbol) {
            for (let i = 0; i < 3; i++) {
                const cell = document.querySelector(`.cell[data-row="${i}"][data-col="${i}"]`);
                if (cell) cell.classList.add('winning');
            }
            return;
        }
        
        // Проверка побочной диагонали
        if (board[0][2] === symbol && board[1][1] === symbol && board[2][0] === symbol) {
            for (let i = 0; i < 3; i++) {
                const cell = document.querySelector(`.cell[data-row="${i}"][data-col="${2-i}"]`);
                if (cell) cell.classList.add('winning');
            }
        }
    },

    /**
     * Обновление статусной строки
     * Показывает, чей сейчас ход
     */
    updateStatus() {
        const status = document.getElementById('status');
        const symbol = this.playerNum === 0 ? 'X' : 'O';
        const isMyTurn = this.currentPlayer === this.playerNum;
        
        console.log('📝 Updating status - My turn:', isMyTurn);
        
        if (isMyTurn) {
            status.textContent = `Вы играете за ${symbol} | ✅ Ваш ход`;
            status.style.color = '#00ff00';  // Зелёный для своего хода
            status.style.fontWeight = 'bold';
        } else {
            status.textContent = `Вы играете за ${symbol} | ⏳ Ход противника`;
            status.style.color = '#ffff00';  // Жёлтый для хода противника
            status.style.fontWeight = 'bold';
        }
    },

    /**
     * Обновление бейджей игроков
     * Подсвечивает текущего активного игрока
     */
    updatePlayerBadges() {
        const playerX = document.getElementById('playerX');
        const playerO = document.getElementById('playerO');
        
        // Сбрасываем подсветку
        playerX.classList.remove('current-turn');
        playerO.classList.remove('current-turn');
        
        // Подсвечиваем текущего игрока
        if (this.currentPlayer === 0) {
            playerX.classList.add('current-turn');
            console.log('🔵 Player X turn');
        } else {
            playerO.classList.add('current-turn');
            console.log('🔴 Player O turn');
        }
    },

    /**
     * Запуск polling для обновления состояния
     * Опрашивает сервер каждую секунду
     */
    startPolling() {
        this.stopPolling();  // Останавливаем предыдущий polling
        
        console.log('🔄 Starting polling every 1 second...');
        this.pollInterval = setInterval(() => {
            console.log('📡 Polling for updates...');
            this.forceUpdate();
        }, 1000);  // Интервал 1 секунда
    },

    /**
     * Остановка polling
     */
    stopPolling() {
        if (this.pollInterval) {
            console.log('🛑 Stopping polling...');
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    },

    /**
     * Принудительное обновление состояния игры
     * Используется в polling и после ходов
     */
    forceUpdate() {
        if (!this.gameId) {
            console.log('❌ No game ID, stopping polling');
            this.stopPolling();
            return;
        }
        
        console.log('🔁 Force updating game state...');
        fetch('/game_state')
            .then(r => {
                if (!r.ok) throw new Error('Network error');
                return r.json();
            })
            .then(state => {
                if (state.status === 'success') {
                    this.updateGameState(state);
                } else {
                    console.log('❌ Game no longer exists:', state.message);
                    this.stopPolling();
                    this.redirectToLobby();
                }
            })
            .catch(error => {
                console.error('💥 Polling error:', error);
            });
    },

    /**
     * Выход из игры и возврат в лобби
     */
    returnToLobby() {
        console.log('🚪 Returning to lobby...');
        this.stopPolling();
        
        // Уведомляем сервер о выходе
        fetch('/leave_room', { method: 'POST' })
            .then(() => {
                this.redirectToLobby();
            })
            .catch(error => {
                console.error('💥 Error leaving room:', error);
                this.redirectToLobby();
            });
    },

    /**
     * Перенаправление в лобби
     */
    redirectToLobby() {
        console.log('🔀 Redirecting to lobby...');
        window.location.href = '/lobby';
    }
};

// Инициализация игры при загрузке DOM
document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM loaded, starting game...');
    game.init();
});

// Обновление состояния при возвращении на вкладку
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && game.pollInterval) {
        console.log('👀 Page became visible, forcing update...');
        game.forceUpdate();
    }
});