# CryptoTracker CLI
## Отчёт о разработке и сравнении версий Qwen и DeepSeek

```
 _____                  _      _____              _             
/  __ \                | |    |_   _|            | |            
| /  \/_ __ _   _ _ __ | |_ ___ | |_ __ __ _  ___| | _____ _ __ 
| |   | '__| | | | '_ \| __/ _ \| | '__/ _` |/ __| |/ / _ \ '__|
| \__/\ |  | |_| | |_) | || (_) | | | | (_| | (__|   <  __/ |   
 \____/_|   \__, | .__/ \__\___/\_/_|  \__,_|\___|_|\_\___|_|   
             __/ | |                                            
            |___/|_|                                               
                      CLI for crypto and fiat exchange rates
```

> **Учебный проект** | Программирование на Python | 2026  
> **Задача:** реализовать CLI-приложение по одному техническому заданию с помощью двух нейросетей и сравнить получившиеся версии.

---

## Содержание

1. [О проекте](#1-о-проекте)
2. [Использованные материалы](#2-использованные-материалы)
3. [Быстрый старт](#3-быстрый-старт)
4. [Сравнение Qwen и DeepSeek](#4-сравнение-qwen-и-deepseek)
5. [Структура папок](#5-структура-папок)
6. [Команды CLI](#6-команды-cli)
7. [API сервера](#7-api-сервера)
8. [Тестирование](#8-тестирование)
9. [Итоги и выводы](#9-итоги-и-выводы)
10. [Лицензия](#10-лицензия)

---

## 1. О проекте

**CryptoTracker** — CLI-приложение для отслеживания курсов фиатных валют и криптовалют, конвертации сумм, ведения истории запросов, работы со списками отслеживания и экспорта данных.

Обе версии используют общий стек:

- **Python**: Qwen заявляет `3.10+`, DeepSeek заявляет `3.11+`
- **CLI**: Typer
- **Вывод в терминал**: Rich
- **Backend**: FastAPI
- **База данных**: SQLite
- **ORM**: SQLAlchemy
- **HTTP-клиент**: httpx
- **Валидация**: Pydantic
- **Внешние API**: Frankfurter API для фиата, CoinGecko API для криптовалют

### Документы проекта

| Файл | Описание |
|------|----------|
| [`qwen/tz.md`](qwen/tz.md) | Техническое задание версии Qwen |
| [`qwen/README.md`](qwen/README.md) | Документация и запуск версии Qwen |
| [`deepseek/tz.md`](deepseek/tz.md) | Техническое задание версии DeepSeek |
| [`deepseek/README.md`](deepseek/README.md) | Документация и запуск версии DeepSeek |

---

## 2. Использованные материалы

Обе папки содержат реализацию одного проекта **CryptoTracker**, но с разной архитектурной детализацией и разными пользовательскими сценариями.

### Промпты

1 prompt
```
Ты — системный архитектор. Напиши детальное техническое задание (ТЗ) для разработки CLI-приложения на Python под названием `CryptoTracker`.

Приложение должно соответствовать следующим рамкам:
1. Внешние REST API: Frankfurter (фиатные валюты) и CoinGecko (криптовалюты). Оба API используются БЕЗ API-ключей.
2. Собственный бэкэнд: FastAPI сервер + SQLAlchemy + SQLite, который хранит историю запросов пользователей и настроенные списки отслеживания валютных пар.
3. CLI интерфейс должен быть написан строго на Typer с красивой визуализацией через Rich (цветные таблицы, прогресс-бары, логи).
4. Клиент должен поддерживать ровно 7 команд (server, rate, convert, history, watch, list-watch, export).

Твоя задача в этом ТЗ самостоятельно спроектировать:
- Оптимальную структуру базы данных (таблицы, связи).
- Архитектуру API эндпоинтов (какие методы, пути и JSON-тела запросов будут у FastAPI сервера).
- Структуру файлов проекта.
- Логику обработки ошибок (если сервер лежит, если внешнее API недоступно и т.д.).
- Формат вывода команд в CLI (как Rich должен красить таблицы).

Оформи ТЗ в виде подробного файла `tz.md`. Не пиши сейчас код самого приложения, только детальное проектирование.
```

2 prompt

```
Отлично, ТЗ готово. Теперь роль Senior-программиста: реализуй весь проект CryptoTracker в нашей папке строго по твоему файлу `tz.md`.

Два главных правила:
1. Пиши ПОЛНЫЙ, рабочий код без каких-либо сокращений, пропусков и плейсхолдеров типа "# здесь ваш код / реализуйте сами". Любой файл должен быть готов к запуску.
2. Обязательно создай файл `README.md` с быстрой инструкцией, как установить зависимости и запустить проект.

Создавай файлы и пиши код прямо сейчас.
```

3 prompt

```
Мне нужно полностью протестировать наш проект `CryptoTracker` и получить проходящие зеленые тесты в pytest. 1. Напиши структуру тестов в папке `tests/`. Тесты должны использовать `pytest`. Напиши минимум 5 тестов для CLI команд и эндпоинтов. и запусти их проверить и посчитать какие работают, а какие нет
```

### Что было изучено при подготовке отчёта

- `qwen/tz.md`
- `qwen/README.md`
- `deepseek/tz.md`
- `deepseek/README.md`
- фактическая структура папок `qwen` и `deepseek`

### Количество файлов

| Проверка | Qwen | DeepSeek |
|----------|------|----------|
| Файлы без `venv/.venv`, `.pytest_cache`, `__pycache__`, `*.pyc` | 73 | 40 |
| Python-файлы без кэша и окружения | 59 | 27 |
| Python-файлы тестов | 6 | 4 |

---

## 3. Быстрый старт

### Qwen версия

```bash
cd qwen
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
cryptotracker server
```

Во втором терминале:

```bash
cd qwen
venv\Scripts\activate
cryptotracker rate USD EUR,RUB,GBP --type fiat
cryptotracker convert 100 USD EUR
cryptotracker watch add default BTC USD --type crypto
cryptotracker list-watch
cryptotracker history
```

По документации Qwen сервер доступен на `http://localhost:8000`, Swagger UI — `http://localhost:8000/docs`.

### DeepSeek версия

```bash
cd deepseek
python -m venv .venv
.venv\Scripts\activate
pip install -e .
cryptotracker server --port 8420
```

Во втором терминале:

```bash
cd deepseek
.venv\Scripts\activate
cryptotracker rate btc usd
cryptotracker convert btc rub 0.25
cryptotracker watch eth usd
cryptotracker list-watch
cryptotracker history
```

DeepSeek также описывает direct-режим без сервера:

```bash
cryptotracker --no-server rate btc usd
```

По документации DeepSeek сервер доступен на `http://localhost:8420`, Swagger UI — `http://localhost:8420/docs`.

---

## 4. Сравнение Qwen и DeepSeek

### Общие метрики

| Метрика | Qwen | DeepSeek |
|---------|------|----------|
| Требуемая версия Python | `>=3.10` | `>=3.11` |
| Точка входа CLI | `cryptotracker.cli.main:app` | `cryptotracker.main:app` |
| Порт сервера по умолчанию | `8000` | `8420` |
| Архитектура CLI | отдельные команды в `cli/commands/` | основные команды в `cli/commands.py` |
| Архитектура backend | разнесены модели, схемы, роутеры, сервисы, external-клиенты | компактные модели/схемы + роутеры + external API-клиенты |
| Direct/fallback режим без сервера | явно не основной сценарий | заявлен как ключевая возможность |
| Профили пользователей | не выделены как главная фича | есть `--profile` |
| Watchlists | несколько списков с CRUD | один профильный watchlist пар |
| Экспорт | история и watchlist в CSV/JSON | history/watchlist/conversions/all в JSON/CSV |
| Заявленные тесты в README | 96 тестов | 22 теста |

---

### Детальное сравнение

| Критерий | Qwen | DeepSeek | Победитель |
|----------|------|----------|------------|
| **Полнота документации** | README подробно описывает установку, команды, API, коды выхода, валюты и тесты | README компактнее, но хорошо объясняет сценарии и архитектуру | Qwen |
| **Техническое задание** | Очень детальное ТЗ: БД, endpoints, ошибки, структура, CLI-команды | ТЗ структурировано, короче, хорошо объясняет client-server и direct-режим | Qwen |
| **Компактность проекта** | Больше файлов и более детальная декомпозиция | Меньше файлов, проще изучать целиком | DeepSeek |
| **Архитектурная декомпозиция** | Отдельные слои `client`, `server`, `services`, `external`, `common`, `cli/commands` | Более плоская структура, часть логики собрана в крупных файлах | Qwen |
| **Удобство быстрого запуска** | Классический сценарий: сервер в одном терминале, CLI во втором | Есть direct-режим `--no-server`, можно проверить курс без сервера | DeepSeek |
| **Работа с профилями** | В README не заявлена как ключевая возможность | Есть `--profile` для изоляции данных | DeepSeek |
| **Тесты** | README заявляет 96 тестов; локальный прогон завершился успешно при `-s` | README заявляет 22 теста; локально не проверено из-за отсутствия `pytest` | Qwen |
| **API дизайн** | REST API под `/api/v1`, больше CRUD-операций для watchlists и currencies | REST API под `/api`, проще и компактнее | Ничья |
| **Подходит новичку** | Больше готовых команд и пояснений, но проект крупнее | Меньше файлов и direct-режим, но README на английском | Ничья |
| **Подходит для изучения слоистой архитектуры** | Хорошо видно разделение сервисов, роутеров, схем и клиентов | Хорошо видно минимальную архитектуру CLI + API | Qwen |

---

### Когда использовать Qwen

- Нужна более подробная учебная реализация с разнесением ответственности по файлам.
- Важно видеть отдельные сервисы backend-логики.
- Нужна подробная русскоязычная документация.
- Нужна версия, где тесты уже можно прогнать в существующем окружении.

### Когда использовать DeepSeek

- Нужна компактная версия, которую проще прочитать целиком.
- Важен direct-режим без обязательного запуска FastAPI-сервера.
- Нужны пользовательские профили через `--profile`.
- Нужна простая архитектура CLI + server + external API clients без большого количества файлов.

---

## 5. Структура папок

### Qwen версия

```text
qwen/
├── cryptotracker/
│   ├── __main__.py
│   ├── cli/
│   │   ├── main.py
│   │   ├── commands/
│   │   └── utils/
│   ├── client/
│   │   ├── api_client.py
│   │   └── exceptions.py
│   ├── server/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   ├── services/
│   │   └── external/
│   └── common/
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_cli.py
│   ├── test_models.py
│   └── test_validators.py
├── data/
├── logs/
├── requirements.txt
├── pyproject.toml
├── tz.md
└── README.md
```

Qwen делает ставку на более подробную слоистую структуру: отдельные сервисы, отдельные схемы, отдельные модели, отдельные внешние API-клиенты и отдельные CLI-команды.

### DeepSeek версия

```text
deepseek/
├── cryptotracker/
│   ├── main.py
│   ├── config.py
│   ├── cli/
│   │   ├── commands.py
│   │   ├── formatting.py
│   │   └── errors.py
│   ├── server/
│   │   ├── app.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── routers/
│   └── api/
│       ├── client.py
│       ├── frankfurter.py
│       └── coingecko.py
├── tests/
│   ├── conftest.py
│   ├── test_api_endpoints.py
│   └── test_cli_commands.py
├── data/
├── pyproject.toml
├── tz.md
└── README.md
```

DeepSeek делает ставку на компактность: меньше файлов, меньше уровней вложенности, direct-режим и профильную модель использования.

---

## 6. Команды CLI

### Общие команды проекта

| Команда | Qwen | DeepSeek | Назначение |
|---------|------|----------|------------|
| `server` | есть | есть | запуск FastAPI-сервера |
| `rate` | есть | есть | получение текущего курса |
| `convert` | есть | есть | конвертация суммы |
| `history` | есть | есть | просмотр истории запросов |
| `watch` | есть | есть | управление отслеживаемыми парами |
| `list-watch` | есть | есть | просмотр watchlist |
| `export` | есть | есть | экспорт данных |

### Примеры Qwen

```bash
cryptotracker rate USD EUR,RUB,GBP --type fiat
cryptotracker rate BTC USD,EUR,ETH --type all
cryptotracker convert 100 USD EUR
cryptotracker watch create crypto_portfolio --description "My crypto investments"
cryptotracker watch add default BTC USD --type crypto
cryptotracker list-watch --sort change
cryptotracker export history csv --output my_history.csv
```

### Примеры DeepSeek

```bash
cryptotracker rate btc usd
cryptotracker convert btc rub 0.25
cryptotracker watch eth usd
cryptotracker watch eth usd --remove
cryptotracker list-watch
cryptotracker history --limit 10 --command rate
cryptotracker export --format csv --dataset history --output history.csv
cryptotracker --profile personal rate btc usd
cryptotracker --no-server rate btc usd
```

### Сравнительная таблица

| Что проверить                              | Qwen                                                                                 | DeepSeek                                                                                               | Что сравнивать |
|--------------------------------------------|--------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|----------------|
| **Запуск сервера**                         | `cryptotracker server`                                                               | `cryptotracker server --port 8420`                                                                      | Старт без ошибок, адрес docs, логирование |
| **Help проекта**                           | `cryptotracker --help`                                                               | `cryptotracker --help`                                                                                  | Полнота справки, список команд |
| **Help команды rate**                      | `cryptotracker rate --help`                                                          | `cryptotracker rate --help`                                                                             | Аргументы, опции, понятность |
| **Курс фиат → фиат**                       | `cryptotracker rate USD EUR,RUB,GBP --type fiat`                                     | `cryptotracker rate usd eur`                                                                            | Формат таблицы/панели, поддержка нескольких валют |
| **Курс фиат → крипта**                     | `cryptotracker rate EUR BTC,ETH,SOL --type crypto`                                   | `cryptotracker rate eur btc`                                                                            | Умеет ли работать с криптой, качество вывода |
| **Курс крипта → фиат**                     | `cryptotracker rate BTC USD --type crypto`                                          | `cryptotracker rate btc usd`                                                                            | Источник CoinGecko, формат курса |
| **Конвертация фиат**                       | `cryptotracker convert 100 USD EUR`                                                  | `cryptotracker convert usd eur 100`                                                                     | Разница порядка аргументов, вывод результата |
| **Конвертация крипта**                     | `cryptotracker convert 1 BTC ETH --type crypto`                                     | `cryptotracker convert btc eth 1`                                                                       | Работа crypto‑to‑crypto |
| **История запросов**                       | `cryptotracker history`                                                              | `cryptotracker history`                                                                                 | Сохраняются ли предыдущие команды |
| **История с лимитом**                      | `cryptotracker history --limit 5`                                                    | `cryptotracker history --limit 5`                                                                       | Пагинация/ограничение вывода |
| **Фильтр истории**                         | `cryptotracker history --command convert`                                            | `cryptotracker history --command convert`                                                               | Работает ли фильтрация |
| **Создание watchlist**                     | `cryptotracker watch create crypto_portfolio --description "Crypto"`                | *Не требуется*                                                                                           | У Qwen есть отдельные watchlists, у DeepSeek проще |
| **Добавить в watchlist**                   | `cryptotracker watch add default BTC USD --type crypto`                             | `cryptotracker watch btc usd`                                                                           | Разница модели watchlist |
| **Показать watchlist**                     | `cryptotracker watch show default`                                                   | `cryptotracker list-watch`                                                                              | Вывод текущих курсов в списке |
| **Список watchlists**                      | `cryptotracker watch list` *или* `cryptotracker list-watch`                         | `cryptotracker list-watch`                                                                              | У Qwen несколько списков, у DeepSeek профильный список |
| **Удалить из watchlist**                   | `cryptotracker watch remove default BTC USD`                                         | `cryptotracker watch btc usd --remove`                                                                  | Удобство удаления пары |
| **Экспорт истории JSON**                   | `cryptotracker export history json --output qwen_history.json`                      | `cryptotracker export --format json --dataset history --output deepseek_history.json`                | Структура экспортируемого JSON |
| **Экспорт истории CSV**                    | `cryptotracker export history csv --output qwen_history.csv`                        | `cryptotracker export --format csv --dataset history --output deepseek_history.csv`                  | CSV‑формат, поля, читаемость |
| **Экспорт watchlist**                      | `cryptotracker export watchlist json --watchlist-name default`                      | `cryptotracker export --format json --dataset watchlist --output deepseek_watch.json`                 | Какие данные попадают в экспорт |
| **Direct‑режим без сервера**               | *Не основной сценарий*                                                               | `cryptotracker --no-server rate btc usd`                                                                | Главное преимущество DeepSeek |
| **Профили**                                | *Не основной сценарий*                                                               | `cryptotracker --profile personal rate btc usd`                                                         | Изоляция истории/данных по профилям |

---

| Блок                | Qwen                                                            | DeepSeek                                                                                 |
|---------------------|-----------------------------------------------------------------|------------------------------------------------------------------------------------------|
| **Сервер**          | `cryptotracker server`                                          | `cryptotracker server --port 8420`                                                       |
| **Фиат**            | `cryptotracker rate USD EUR,RUB,GBP --type fiat`                | `cryptotracker rate usd eur`                                                             |
| **Крипта**          | `cryptotracker rate BTC USD --type crypto`                     | `cryptotracker rate btc usd`                                                             |
| **Конвертация**     | `cryptotracker convert 100 USD EUR`                             | `cryptotracker convert usd eur 100`                                                      |
| **История**         | `cryptotracker history --limit 5`                               | `cryptotracker history --limit 5`                                                        |
| **Watchlist**       | `cryptotracker watch add default BTC USD --type crypto`        | `cryptotracker watch btc usd`                                                            |
| **Просмотр watchlist**| `cryptotracker watch show default`                           | `cryptotracker list-watch`                                                               |
| **Экспорт**         | `cryptotracker export history json --output qwen_history.json` | `cryptotracker export --format json --dataset history --output deepseek_history.json`    |
| **Уникальная фича** | `cryptotracker watch create crypto_portfolio --description "Crypto"` | `cryptotracker --no-server rate btc usd`                                              |

---

## 7. API сервера

### Qwen API

Qwen использует базовый URL `http://localhost:8000` и API-префикс `/api/v1`.

| Метод | Путь | Назначение |
|-------|------|------------|
| `GET` | `/health` | health check |
| `GET` | `/api/v1/rates` | получить курсы |
| `POST` | `/api/v1/convert` | конвертация |
| `GET` | `/api/v1/history` | история |
| `DELETE` | `/api/v1/history` | очистка истории |
| `GET` | `/api/v1/watchlists` | список watchlists |
| `POST` | `/api/v1/watchlists` | создать watchlist |
| `GET` | `/api/v1/watchlists/{id}` | детали watchlist |
| `DELETE` | `/api/v1/watchlists/{id}` | удалить watchlist |
| `POST` | `/api/v1/watchlists/{id}/items` | добавить пару |
| `DELETE` | `/api/v1/watchlists/{id}/items/{item_id}` | удалить пару |
| `GET` | `/api/v1/currencies` | список валют |
| `POST` | `/api/v1/currencies/sync` | синхронизация валют |
| `GET` | `/api/v1/export/history` | экспорт истории |
| `GET` | `/api/v1/export/watchlist/{id}` | экспорт watchlist |

### DeepSeek API

DeepSeek использует базовый URL `http://localhost:8420/api`.

| Метод | Путь | Назначение |
|-------|------|------------|
| `GET` | `/server/status` | health check и статус внешних API |
| `GET` | `/currencies` | список фиатных валют |
| `GET` | `/crypto` | список криптовалют |
| `GET` | `/rate?base=X&target=Y` | получить курс |
| `POST` | `/convert` | конвертация |
| `GET` | `/history` | история |
| `POST` | `/watch` | добавить пару в watchlist |
| `GET` | `/watch` | список watchlist с курсами |
| `DELETE` | `/watch/{id}` | удалить пару |
| `GET` | `/export` | экспорт данных |

---

## 8. Тестирование

### Qwen

В `qwen/README.md` заявлено **96 тестов**:

| Файл | Тестов по README | Назначение |
|------|------------------|------------|
| `test_validators.py` | 30 | валидаторы CLI |
| `test_cli.py` | 20 | CLI-команды |
| `test_api.py` | 25 | FastAPI endpoints |
| `test_models.py` | 21 | модели и исключения |

Команда проверки:

```bash
cd qwen
venv\Scripts\activate
python -m pytest tests -q -s
```

### DeepSeek

В `deepseek/README.md` заявлено **22 теста**:

| Файл | Тестов по README | Назначение |
|------|------------------|------------|
| `test_cli_commands.py` | 10 | CLI-команды |
| `test_api_endpoints.py` | 12 | API endpoints |

Команда проверки после установки dev-зависимостей:

```bash
cd deepseek
.venv\Scripts\activate
pip install -e ".[dev]"
pytest tests -v
```

### Результаты

Qwen написал 96 тестов на pytest и после пары правок все прошел успешно.

Deepseek написал 22 теста, потребовал дополнительно потратить 5 миллионов токенов для успешного прохождения тестов.

---

## 9. Итоги и выводы

### Главные выводы

**1. Обе версии решают одну задачу**  
Qwen и DeepSeek реализуют CLI для курсов валют, конвертации, истории, watchlist, экспорта и локального FastAPI-сервера.

**2. Qwen подробнее и ближе к учебному enterprise-варианту**  
Версия Qwen сильнее декомпозирована: отдельные команды, сервисы, схемы, модели, внешние клиенты и общие утилиты. Она лучше подходит для демонстрации слоистой архитектуры.

**3. DeepSeek компактнее и удобнее для быстрого сценария**  
Версия DeepSeek меньше по количеству файлов, проще читается, содержит direct-режим `--no-server` и поддержку профилей через `--profile`.

**4. Выбор зависит от цели**  
Для сдачи с акцентом на полноту документации и архитектуру лучше выглядит Qwen. Для демонстрации компактного CLI с fallback-режимом лучше выглядит DeepSeek.

### Итоговый счёт

| Категория | Qwen | DeepSeek |
|-----------|:----:|:--------:|
| Подробность ТЗ | ✅ | ➖ |
| Подробность README | ✅ | ➖ |
| Компактность | ➖ | ✅ |
| Direct-режим без сервера | ➖ | ✅ |
| Профили пользователей | ➖ | ✅ |
| Слоистая архитектура | ✅ | ➖ |
| Простота чтения всего проекта | ➖ | ✅ |
| **Итого** | **4 / 7** | **3 / 7** |

### Финальный вердикт

Если нужен **более полный учебный проект с подробной архитектурой и проверенными тестами**, выбирайте **Qwen**.

Если нужен **более компактный проект с direct-режимом и профилями**, выбирайте **DeepSeek**.

---

## 10. Лицензия

Обе версии заявляют лицензию **MIT**.


---

*Проект выполнен в рамках учебного сравнения реализаций, сгенерированных разными нейросетями.*
