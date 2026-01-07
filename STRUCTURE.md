# Структура проекта торгового бота

```
BOT-TRADER/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI приложение, точка входа
│   │
│   ├── webhook/                   # Модуль обработки вебхуков
│   │   ├── __init__.py
│   │   ├── handler.py             # Обработчик вебхуков от TradingView
│   │   └── validator.py           # Валидация входящих вебхуков
│   │
│   ├── parser/                    # Парсинг алертов
│   │   ├── __init__.py
│   │   └── tradingview.py         # Парсинг сообщений от TradingView
│   │
│   ├── exchange/                  # Работа с биржами через CCXT
│   │   ├── __init__.py
│   │   ├── client.py              # Обертка над CCXT клиентом
│   │   ├── factory.py             # Фабрика для создания клиентов разных бирж
│   │   ├── order_manager.py      # Управление ордерами (market, limit, stop)
│   │   └── position_manager.py   # Управление позициями (установка плеча)
│   │
│   ├── models/                    # Модели данных (Pydantic)
│   │   ├── __init__.py
│   │   ├── webhook.py             # Модель вебхука от TradingView
│   │   ├── trade.py               # Модель торгового сигнала
│   │   └── order.py               # Модель ордера
│   │
│   ├── config/                    # Конфигурация
│   │   ├── __init__.py
│   │   └── settings.py            # Настройки (API ключи, биржи, лимиты)
│   │
│   ├── utils/                      # Утилиты
│   │   ├── __init__.py
│   │   ├── logger.py              # Настройка логирования
│   │   ├── risk_manager.py        # Управление рисками (проверка лимитов)
│   │   └── indicators.py          # Расчет технических индикаторов (ATR)
│   │
│
├── tests/                          # Тесты
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_webhook.py
│   └── test_exchange.py
│
├── .env                            # Переменные окружения (не коммитить!)
├── .env.example                    # Пример конфигурации
├── requirements.txt                # Зависимости Python
├── README.md                       # Документация
└── .gitignore                      # Игнорируемые файлы
```

## Описание модулей

### 1. `app/main.py`
- FastAPI приложение
- Роуты для вебхуков
- Health check endpoint
- Middleware для логирования

### 2. `app/webhook/handler.py`
- Прием POST запросов от TradingView
- Валидация токена из query параметра (`?token=secret_token`)
- Извлечение текста алерта из тела запроса
- Вызов парсера и обработчика ордеров

### 3. `app/parser/tradingview.py`
- Парсинг текста алерта от TradingView
- Формат: `SYMBOL Crossing Up/Down PRICE [size=SIZE] [lev=LEVERAGE] [EXCHANGE]`
- Примеры:
  - `LTCUSDT Crossing Down 76.47` → шорт, цена 76.47
  - `LTCUSDT Crossing Up 76.47 size=100` → лонг, цена 76.47, размер 100
  - `LTCUSDT Crossing Up 76.47 size=100 lev=35` → лонг, цена 76.47, размер 100, плечо 35
  - `LTCUSDT Crossing Down 76.49 Bybit` → шорт, цена 76.49, биржа Bybit
- Извлечение: символ, направление (LONG/SHORT), цена входа, размер позиции, кредитное плечо, биржа
- Если биржа не указана в алерте, используется значение по умолчанию из .env

### 4. `app/exchange/client.py`
- Базовый класс для работы с CCXT
- Инициализация клиента для конкретной биржи
- Подключение к бирже (Binance, OKX, BYBIT, Bitget)
- Получение баланса, информации о символе
- Установка режима тестинга (sandbox)

### 4.1. `app/exchange/factory.py`
- Фабрика для создания клиентов разных бирж
- Управление пулом подключений к биржам
- Выбор биржи на основе конфигурации или символа

### 5. `app/exchange/order_manager.py`
- Выставление market ордеров для входа в позицию
- Установка кредитного плеча перед открытием позиции
- Расчет стоп-лосс и тейк-профит на основе ATR:
  - Стоп-лосс = цена входа ± (10% от среднего ATR)
  - Тейк-профит = цена входа ± (30% от среднего ATR)
- Выставление стоп-лосс и тейк-профит ордеров
- Проверка статуса ордеров
- Обработка ошибок и retry логика
- Поддержка фьючерсных контрактов (USDT-M или COIN-M)

### 6. `app/models/`
- Pydantic модели для валидации данных
- `TradingViewWebhook` - структура входящего вебхука
- `TradeSignal` - распарсенный торговый сигнал
- `OrderRequest` - запрос на создание ордера

### 7. `app/config/settings.py`
- Загрузка переменных окружения
- Настройки для каждой биржи (Binance, OKX, BYBIT, Bitget):
  - API ключи (apiKey, secret, passphrase для OKX)
  - Режим работы (sandbox/production)
  - Настройки по умолчанию (стоп-лосс %, тейк-профит %)
- Лимиты риска (макс. размер позиции, макс. количество открытых позиций)
- Секретный токен для вебхуков

### 8. `app/utils/risk_manager.py`
- Проверка лимитов перед выставлением ордера
- Проверка баланса
- Проверка максимального количества открытых позиций

### 9. `app/utils/indicators.py`
- Расчет технических индикаторов
- Расчет среднего ATR (Average True Range) для символа
- Получение исторических данных через CCXT для расчета ATR
- Период ATR настраивается через .env (ATR_PERIOD, по умолчанию 5)
- Расчет ATR выполняется при каждом запросе (без кэширования)

## Поток данных

```
TradingView Alert 
    ↓
POST /webhook/tradingview?token=SECRET
    ↓
webhook/handler.py (валидация токена)
    ↓
parser/tradingview.py (парсинг сообщения)
    ↓
utils/indicators.py (получение ATR для символа)
    ↓
utils/risk_manager.py (проверка рисков)
    ↓
exchange/order_manager.py (расчет SL/TP на основе ATR)
    ↓
exchange/order_manager.py (установка плеча, открытие позиции)
    ↓
exchange/order_manager.py (выставление стоп-лосс и тейк-профит)
    ↓
exchange/client.py (CCXT → биржа)
```

## Формат алерта от TradingView

### Формат сообщения:
```
SYMBOL Crossing Up/Down PRICE [size=SIZE] [lev=LEVERAGE] [EXCHANGE]
```

### Примеры:
- `LTCUSDT Crossing Down 76.47` → Шорт позиция, цена входа 76.47
- `LTCUSDT Crossing Up 76.47 size=100` → Лонг позиция, цена 76.47, размер 100 USDT
- `LTCUSDT Crossing Up 76.47 size=100 lev=35` → Лонг позиция, цена 76.47, размер 100 USDT, плечо 35x
- `LTCUSDT Crossing Down 76.49 Bybit` → Шорт позиция, цена 76.49, биржа Bybit
- `LTCUSDT Crossing Up 76.47 size=100 lev=35 Binance` → Лонг, цена 76.47, размер 100, плечо 35x, биржа Binance

### Парсинг:
- `Crossing Up` → LONG позиция
- `Crossing Down` → SHORT позиция
- `size=X` → размер позиции в USDT (опционально, если нет - из .env)
- `lev=X` → кредитное плечо (опционально, если нет - из .env)
- `Bybit/Binance/OKX/Bitget` → биржа (опционально, если нет - из .env EXCHANGE)

### Вебхук:
- Endpoint: `POST /webhook/tradingview?token=SECRET_TOKEN`
- Тело запроса: обычно JSON с полем `message` или `text`, содержащим текст алерта
- Валидация токена из query параметра

## Поддерживаемые биржи

- **Binance** - фьючерсы (USDT-M или COIN-M)
- **OKX** - фьючерсы
- **BYBIT** - фьючерсы
- **Bitget** - фьючерсы

Каждая биржа требует свои API ключи и может иметь особенности в работе с ордерами.

## Безопасность

- Проверка токена из query параметра (`?token=SECRET_TOKEN`)
- Валидация всех входящих данных
- Лимиты на размер позиций
- Логирование всех операций
- Защита от повторной обработки одного алерта (опционально)

## Конфигурация (.env)

```env
# Секрет для вебхуков
WEBHOOK_SECRET_TOKEN=your_secret_token_here

# Binance
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
BINANCE_SANDBOX=false

# OKX
OKX_API_KEY=your_key
OKX_API_SECRET=your_secret
OKX_PASSPHRASE=your_passphrase
OKX_SANDBOX=false

# BYBIT
BYBIT_API_KEY=your_key
BYBIT_API_SECRET=your_secret
BYBIT_SANDBOX=false

# Bitget
BITGET_API_KEY=your_key
BITGET_API_SECRET=your_secret
BITGET_PASSPHRASE=your_passphrase
BITGET_SANDBOX=false

# Настройки по умолчанию
EXCHANGE=binance  # Биржа по умолчанию (binance, okx, bybit, bitget)
CONTRACT_TYPE=USDT-M  # Тип контракта: USDT-M или COIN-M
SIZE_POSITION=100  # Размер позиции по умолчанию в USDT
DEFAULT_LEVERAGE=10  # Плечо по умолчанию, если не указано в алерте

# Расчет стоп-лосс и тейк-профит на основе ATR
ATR_PERIOD=5  # Период для расчета ATR (по умолчанию 5)
STOP_LOSS_RATE=0.10  # 10% от среднего ATR для стоп-лосса
TAKE_PROFIT_RATE=0.30  # 30% от среднего ATR для тейк-профита

# Лимиты риска
MAX_POSITION_SIZE=1000  # Максимальный размер позиции в USDT
```

## Расчет стоп-лосс и тейк-профит

### Формула:
1. Получаем средний ATR (Average True Range) для символа через исторические данные
2. **Стоп-лосс:**
   - Для LONG: `цена_входа - (ATR * STOP_LOSS_RATE)`
   - Для SHORT: `цена_входа + (ATR * STOP_LOSS_RATE)`
3. **Тейк-профит:**
   - Для LONG: `цена_входа + (ATR * TAKE_PROFIT_RATE)`
   - Для SHORT: `цена_входа - (ATR * TAKE_PROFIT_RATE)`

### Пример:
- Цена входа: 76.47 USDT
- Средний ATR: 2.5 USDT
- STOP_LOSS_RATE: 0.10 (10%)
- TAKE_PROFIT_RATE: 0.30 (30%)

Для LONG позиции:
- Стоп-лосс: 76.47 - (2.5 * 0.10) = 76.22 USDT
- Тейк-профит: 76.47 + (2.5 * 0.30) = 77.22 USDT

### Получение ATR:
- Используется CCXT для получения исторических данных (OHLCV)
- Расчет ATR по стандартной формуле с периодом из .env (ATR_PERIOD, по умолчанию 5)
- Расчет выполняется при каждом алерте (без кэширования)
- Для расчета ATR требуется достаточное количество свечей (обычно период + несколько дополнительных)

