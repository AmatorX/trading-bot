# Trading Bot - Торговый бот для фьючерсной торговли

Торговый бот для автоматической торговли фьючерсами на биржах Binance, OKX, BYBIT и Bitget на основе алертов от TradingView.

## Возможности

- Прием вебхуков от TradingView
- Парсинг торговых сигналов из алертов
- Автоматическое открытие позиций на биржах
- Автоматическая установка стоп-лосс и тейк-профит на основе ATR
- Поддержка множественных бирж (Binance, OKX, BYBIT, Bitget)
- Управление рисками

## Установка

### Вариант 1: Docker с Caddy (рекомендуется для продакшена)

Проект использует Caddy как reverse proxy для автоматического HTTPS.

1. Клонируйте репозиторий или скопируйте файлы проекта

2. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

3. Заполните `.env` файл своими API ключами и настройками

4. Убедитесь, что `Caddyfile` настроен с вашим доменом (по умолчанию `ainol.xyz`)

5. Соберите и запустите контейнеры:
```bash
docker-compose up -d --build
```

6. Проверьте статус:
```bash
docker-compose ps
docker-compose logs -f trading-bot
docker-compose logs -f caddy
```

7. Остановка:
```bash
docker-compose down
```

**Примечание:** Caddy автоматически получит SSL сертификат для вашего домена через Let's Encrypt. Убедитесь, что домен указывает на IP вашего VPS.

### Вариант 2: Локальная установка

1. Клонируйте репозиторий или скопируйте файлы проекта

2. Создайте виртуальное окружение:
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

5. Заполните `.env` файл своими API ключами и настройками

## Конфигурация

### Основные настройки в `.env`:

- `WEBHOOK_SECRET_TOKEN` - секретный токен для защиты вебхуков
- `EXCHANGE` - биржа по умолчанию (binance, okx, bybit, bitget)
- `CONTRACT_TYPE` - тип контракта (USDT-M или COIN-M)
- `SIZE_POSITION` - размер позиции по умолчанию в USDT
- `DEFAULT_LEVERAGE` - кредитное плечо по умолчанию
- `ATR_PERIOD` - период для расчета ATR (по умолчанию 5)
- `STOP_LOSS_RATE` - коэффициент для стоп-лосс (10% от ATR = 0.10)
- `TAKE_PROFIT_RATE` - коэффициент для тейк-профит (30% от ATR = 0.30)

### API ключи для бирж:

Заполните API ключи для используемых бирж:
- Binance: `BINANCE_API_KEY`, `BINANCE_API_SECRET`
- OKX: `OKX_API_KEY`, `OKX_API_SECRET`, `OKX_PASSPHRASE`
- BYBIT: `BYBIT_API_KEY`, `BYBIT_API_SECRET`
- Bitget: `BITGET_API_KEY`, `BITGET_API_SECRET`, `BITGET_PASSPHRASE`

## Запуск

### Docker:
```bash
docker-compose up -d
```

### Локально:
```bash
python -m app.main
```

Или через uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Проверка работы:
```bash
curl http://localhost:8000/health
```

## Формат алертов TradingView

### Базовый формат:
```
SYMBOL Crossing Up/Down PRICE [size=SIZE] [lev=LEVERAGE] [EXCHANGE]
```

### Примеры:

- `LTCUSDT Crossing Down 76.47` - Шорт позиция, цена входа 76.47
- `LTCUSDT Crossing Up 76.47 size=100` - Лонг позиция, размер 100 USDT
- `LTCUSDT Crossing Up 76.47 size=100 lev=35` - Лонг, размер 100, плечо 35x
- `LTCUSDT Crossing Down 76.49 Bybit` - Шорт, биржа Bybit
- `LTCUSDT Crossing Up 76.47 size=100 lev=35 Binance` - Полный пример

### Параметры:

- `Crossing Up` → LONG позиция
- `Crossing Down` → SHORT позиция
- `size=X` → размер позиции в USDT (опционально)
- `lev=X` → кредитное плечо (опционально)
- `Bybit/Binance/OKX/Bitget` → биржа (опционально)

## Настройка вебхука в TradingView

1. В TradingView создайте алерт
2. В настройках вебхука укажите URL:
   ```
   https://ainol.xyz/webhook/tradingview?token=YOUR_SECRET_TOKEN
   ```
   Где `YOUR_SECRET_TOKEN` - это значение из `.env` файла (`WEBHOOK_SECRET_TOKEN`)
   
   **Важно:** 
   - Используйте HTTPS для продакшена
   - Токен должен совпадать с `WEBHOOK_SECRET_TOKEN` в `.env`
   - Если используете IP вместо домена:
     ```
     http://YOUR_IP:8000/webhook/tradingview?token=YOUR_SECRET_TOKEN
     ```
3. В теле сообщения укажите формат алерта (см. выше)
4. Метод: POST
5. Content-Type: application/json
6. Тело запроса:
   ```json
   {
     "message": "LTCUSDT Crossing Up 77.50 size=100 lev=10"
   }
   ```

### Пример настройки для домена ainol.xyz:

После запуска Docker контейнеров с Caddy, URL вебхука будет:

**URL вебхука:**
```
https://ainol.xyz/webhook/tradingview?token=ВАШ_СЕКРЕТНЫЙ_ТОКЕН
```

**Настройки в TradingView:**
- URL: `https://ainol.xyz/webhook/tradingview?token=ВАШ_ТОКЕН`
- Метод: `POST`
- Content-Type: `application/json`
- Тело: `{"message": "{{message}}"}` или просто текст алерта

**Важно:**
- Caddy автоматически настроит HTTPS через Let's Encrypt
- Убедитесь, что домен `ainol.xyz` указывает на IP вашего VPS
- Порты 80 и 443 должны быть открыты в firewall

## Расчет стоп-лосс и тейк-профит

Бот автоматически рассчитывает стоп-лосс и тейк-профит на основе ATR:

- **Стоп-лосс**: цена входа ± (ATR × STOP_LOSS_RATE)
- **Тейк-профит**: цена входа ± (ATR × TAKE_PROFIT_RATE)

Для LONG:
- Стоп-лосс ниже цены входа
- Тейк-профит выше цены входа

Для SHORT:
- Стоп-лосс выше цены входа
- Тейк-профит ниже цены входа

## API Endpoints

- `GET /` - информация о сервисе
- `GET /health` - проверка здоровья сервиса
- `POST /webhook/tradingview?token=SECRET_TOKEN` - прием вебхуков от TradingView

## Безопасность

- Все вебхуки защищены секретным токеном
- Валидация всех входящих данных
- Лимиты на размер позиций
- Логирование всех операций

## Логирование

Логи сохраняются в папке `logs/` с именем файла `bot_trader_YYYYMMDD.log`

## Поддерживаемые биржи

- **Binance** - фьючерсы USDT-M и COIN-M
- **OKX** - фьючерсы
- **BYBIT** - фьючерсы
- **Bitget** - фьючерсы

## Примечания

- Рекомендуется сначала протестировать на sandbox режиме
- Убедитесь, что у вас достаточно баланса для открытия позиций
- Проверьте настройки лимитов риска перед использованием

## Лицензия

MIT

