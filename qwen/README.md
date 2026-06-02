# CryptoTracker

CLI-приложение для отслеживания курсов криптовалют и фиатных валют с локальным сервером для хранения истории запросов и списков отслеживания.

## Возможности

- 📊 Получение актуальных курсов фиатных валют (Frankfurter API)
- 💰 Отслеживание курсов криптовалют (CoinGecko API)
- 🔄 Конвертация между валютами
- 📝 История всех запросов
- 👁️ Списки отслеживания (watchlists)
- 📤 Экспорт данных в CSV/JSON
- 🎨 Красивый вывод с Rich (таблицы, цвета, прогресс-бары)

## Технологический стек

- **Python 3.10+**
- **Typer** - CLI фреймворк
- **FastAPI** - Backend сервер
- **SQLAlchemy 2.0+** - ORM
- **SQLite** - База данных
- **Rich** - Визуализация
- **httpx** - HTTP клиент
- **Pydantic v2** - Валидация

## Установка

### 1. Клонирование и настройка

```bash
cd CryptoTracker/qwen
```

### 2. Создание виртуального окружения

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Установка приложения в режиме разработки

```bash
pip install -e .
```

### 5. Настройка переменных окружения (опционально)

```bash
copy .env.example .env
# или
cp .env.example .env
```

Отредактируйте `.env` файл при необходимости.

## Использование

### Запуск сервера

**Важно:** Сервер должен быть запущен в отдельном терминале перед использованием CLI команд.

```bash
cryptotracker server
```

Или с параметрами:

```bash
cryptotracker server --host 0.0.0.0 --port 8080 --reload
```

После запуска сервера:
- API будет доступен на `http://localhost:8000`
- Документация Swagger UI: `http://localhost:8000/docs`
- База данных автоматически инициализируется

### CLI команды

#### Получение курсов валют

```bash
# Курсы USD к фиатным валютам
cryptotracker rate USD EUR,RUB,GBP --type fiat

# Курсы BTC к различным валютам
cryptotracker rate BTC USD,EUR,ETH --type all

# Курсы EUR к криптовалютам
cryptotracker rate EUR BTC,ETH,SOL --type crypto
```

#### Конвертация валют

```bash
# Конвертация фиатных валют
cryptotracker convert 100 USD EUR

# Конвертация в криптовалюту
cryptotracker convert 1000 USD BTC --type crypto

# Конвертация между криптовалютами
cryptotracker convert 1 BTC ETH --type crypto
```

#### Просмотр истории

```bash
# Показать последние 20 записей
cryptotracker history

# Показать последние 50 конвертаций
cryptotracker history --limit 50 --command convert

# Показать историю за последнюю неделю
cryptotracker history --from-date 2026-05-19

# Очистить историю старше 30 дней
cryptotracker history --clear-older-than 30

# Очистить всю историю
cryptotracker history --clear
```

#### Управление watchlists

```bash
# Показать все watchlists
cryptotracker watch list

# Показать содержимое watchlist с текущими курсами
cryptotracker watch show default

# Создать новый watchlist
cryptotracker watch create crypto_portfolio --description "My crypto investments"

# Добавить валютную пару
cryptotracker watch add default BTC USD --type crypto
cryptotracker watch add default USD EUR --type fiat

# Удалить валютную пару
cryptotracker watch remove default BTC USD

# Удалить watchlist
cryptotracker watch delete crypto_portfolio
```

#### Просмотр всех watchlists

```bash
# Показать все watchlists
cryptotracker list-watch

# Показать только конкретные watchlists
cryptotracker list-watch --name default --name crypto_portfolio

# Отсортировать по изменению за 24 часа
cryptotracker list-watch --sort change

# Показать только криптовалюты
cryptotracker list-watch --type crypto
```

#### Экспорт данных

```bash
# Экспорт всей истории в CSV
cryptotracker export history csv

# Экспорт истории за последний месяц в JSON
cryptotracker export history json --from-date 2026-04-26 --to-date 2026-05-26

# Экспорт конкретного watchlist в JSON
cryptotracker export watchlist json --watchlist-name default

# Экспорт с указанием выходного файла
cryptotracker export history csv --output my_history.csv
```

## Тестирование

### Запуск тестов

```bash
# Запуск всех тестов
python -m pytest tests/ -v -s

# Запуск с покрытием
python -m pytest tests/ -v -s --cov=cryptotracker --cov-report=term-missing

# Запуск конкретной группы тестов
python -m pytest tests/test_cli.py -v -s       # CLI команды
python -m pytest tests/test_api.py -v -s       # API эндпоинты
python -m pytest tests/test_validators.py -v   # Валидаторы
python -m pytest tests/test_models.py -v       # Модели и исключения
```

> **Примечание:** Флаг `-s` необходим, так как Rich-логгер конфликтует с механизмом захвата вывода pytest.

### Структура тестов

```
tests/
├── conftest.py          # Общие фикстуры (БД, сессии, async-клиент)
├── test_validators.py   # 30 тестов CLI-валидаторов
├── test_cli.py          # 20 тестов CLI-команд (Typer CliRunner)
├── test_api.py          # 25 тестов FastAPI-эндпоинтов (httpx AsyncClient)
└── test_models.py       # 21 тест моделей и исключений
```

**Всего: 96 тестов, все проходят ✅**

| Файл | Тестов | Описание |
|------|--------|----------|
| `test_validators.py` | 30 | Валидация кодов валют, сумм, дат, парсинг списков |
| `test_cli.py` | 20 | Команды rate, convert, history, export, version, help |
| `test_api.py` | 25 | Health, currencies, watchlists, history, rates, convert, export |
| `test_models.py` | 21 | SQLAlchemy модели, иерархия исключений |

## Структура проекта

```
CryptoTracker/
├── cryptotracker/              # Основной пакет (46 .py файлов + 13 __init__.py)
│   ├── __main__.py             # Точка входа python -m cryptotracker
│   ├── cli/                    # CLI интерфейс (Typer)
│   │   ├── main.py             # Главное CLI-приложение
│   │   ├── commands/           # 7 команд CLI (rate, convert, history, watch, list-watch, export, server)
│   │   └── utils/              # Утилиты (display, validators)
│   ├── client/                 # HTTP клиент для backend (api_client, exceptions)
│   ├── server/                 # FastAPI сервер
│   │   ├── main.py             # FastAPI приложение
│   │   ├── database.py         # SQLAlchemy async engine + session
│   │   ├── models/             # 4 SQLAlchemy модели (Currency, Watchlist, WatchlistItem, QueryHistory)
│   │   ├── schemas/            # 5 Pydantic схем (common, currency, rates, history, watchlist)
│   │   ├── routers/            # 6 API роутеров (health, rates, history, watchlists, currencies, export)
│   │   ├── services/           # 4 сервиса (rate, watchlist, history, export)
│   │   └── external/           # 2 внешних API клиента (Frankfurter, CoinGecko)
│   └── common/                 # Общие утилиты (config, exceptions, logger)
├── tests/                      # Тесты (96 тестов, pytest + pytest-asyncio)
│   ├── conftest.py             # Фикстуры (БД, сессии, async HTTP-клиент)
│   ├── test_validators.py      # Тесты валидаторов
│   ├── test_cli.py             # Тесты CLI-команд
│   ├── test_api.py             # Тесты API-эндпоинтов
│   └── test_models.py          # Тесты моделей и исключений
├── data/                       # База данных (создается автоматически)
├── logs/                       # Логи (создается автоматически)
├── requirements.txt            # Зависимости (13 пакетов)
├── pyproject.toml              # Конфигурация проекта + pytest
├── .env.example                # Пример переменных окружения
├── .gitignore                  # Git ignore
└── README.md                   # Документация
```

### Количество структурных файлов

| Категория | Файлов |
|-----------|--------|
| Python-модули (source) | 46 |
| `__init__.py` | 13 |
| Конфигурация и документация | 6 |
| **Всего структурных файлов** | **65** |

**Конфигурация и документация:**
- `.env.example` — пример переменных окружения
- `.gitignore` — правила игнорирования Git
- `pyproject.toml` — конфигурация проекта и pytest
- `requirements.txt` — зависимости (13 пакетов)
- `README.md` — документация
- `tz.md` — техническое задание

## API Endpoints

### Health Check
- `GET /health` - Проверка работоспособности сервера

### Курсы валют
- `GET /api/v1/rates` - Получение актуальных курсов
- `POST /api/v1/convert` - Конвертация валют

### История
- `GET /api/v1/history` - Получение истории запросов
- `DELETE /api/v1/history` - Очистка истории

### Watchlists
- `GET /api/v1/watchlists` - Список всех watchlists
- `POST /api/v1/watchlists` - Создание watchlist
- `GET /api/v1/watchlists/{id}` - Детали watchlist
- `DELETE /api/v1/watchlists/{id}` - Удаление watchlist
- `POST /api/v1/watchlists/{id}/items` - Добавление пары
- `DELETE /api/v1/watchlists/{id}/items/{item_id}` - Удаление пары

### Валюты
- `GET /api/v1/currencies` - Список доступных валют
- `POST /api/v1/currencies/sync` - Синхронизация с API

### Экспорт
- `GET /api/v1/export/history` - Экспорт истории
- `GET /api/v1/export/watchlist/{id}` - Экспорт watchlist

## Конфигурация

Переменные окружения (файл `.env`):

```bash
SERVER_HOST=localhost
SERVER_PORT=8000
DATABASE_URL=sqlite:///./data/cryptotracker.db
FRANKFURTER_TIMEOUT=10
COINGECKO_TIMEOUT=15
MAX_RETRY_ATTEMPTS=3
RETRY_BASE_DELAY=1.0
CACHE_TTL_SECONDS=60
LOG_LEVEL=INFO
LOG_FILE=logs/server.log
```

## Коды выхода CLI

| Код | Описание |
|-----|----------|
| 0   | Успешное выполнение |
| 1   | Ошибка валидации входных данных |
| 2   | Сервер недоступен |
| 3   | Внешний API недоступен |
| 4   | Ресурс не найден |
| 5   | Конфликт данных |
| 6   | Ошибка базы данных |
| 99  | Непредвиденная ошибка |

## Поддерживаемые валюты

### Фиатные (Frankfurter API)
USD, EUR, GBP, JPY, RUB, CNY, CHF, CAD, AUD, INR, BRL, KRW, MXN, SGD, HKD, NOK, NZD, SEK, DKK, PLN, TRY, ZAR, CZK, HUF, ILS, THB, MYR, PHP, IDR, ISK, BGN, RON

### Криптовалюты (CoinGecko API)
BTC (Bitcoin), ETH (Ethereum), BNB (BNB), SOL (Solana), XRP (Ripple), ADA (Cardano), DOGE (Dogecoin), DOT (Polkadot), MATIC (Polygon), LTC (Litecoin)

## Лицензия

MIT

## Автор

Developer (dev@example.com)
