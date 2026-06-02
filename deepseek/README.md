# 💎 CryptoTracker

**CryptoTracker** — console CLI application for tracking fiat and cryptocurrency
exchange rates, converting amounts between currencies, maintaining watchlists,
and exporting data.

---

## Features

- 💱 **Real-time exchange rates** — fiat via [Frankfurter API](https://www.frankfurter.app/),
  crypto via [CoinGecko API](https://www.coingecko.com/) (both free, no API key needed).
- 🔄 **Currency conversion** — convert any amount between any supported currency pair.
- 👁️ **Watchlists** — track favorite currency pairs with live rate updates.
- 📋 **Request history** — every query is logged locally for audit.
- 📦 **Export** — export your data to JSON or CSV.
- 👤 **Multi-profile** — data isolation via named profiles.
- 🎨 **Rich terminal UI** — coloured tables, panels, progress bars.

---

## Quick Start

### Prerequisites

- **Python 3.11+** (check: `python --version`)
- **pip** (comes with Python)

### Installation

```bash
# 1. Clone or download the project
cd cryptotracker

# 2. Create a virtual environment (recommended)
python -m venv .venv

# 3. Activate the virtual environment
#    Windows:
.venv\Scripts\activate
#    Linux / macOS:
source .venv/bin/activate

# 4. Install the package in development mode
pip install -e .
```

After installation, the `cryptotracker` command becomes available globally
inside the virtual environment.

### Configuration (optional)

```bash
# Copy the example config file
copy .env.example .env       # Windows
cp .env.example .env         # Linux / macOS

# Edit .env to customize server port, database path, etc.
```

All settings have sensible defaults, so `.env` is optional.

---

## Usage

### Basic Commands

```bash
# Get current exchange rate
cryptotracker rate btc usd

# Convert 0.25 BTC to RUB
cryptotracker convert btc rub 0.25

# Add a pair to watchlist
cryptotracker watch eth usd

# Show watchlist with live rates
cryptotracker list-watch

# Remove from watchlist
cryptotracker watch eth usd --remove

# Show request history (last 20)
cryptotracker history

# Export all data to JSON
cryptotracker export --format json --output backup.json

# Export history to CSV
cryptotracker export --format csv --dataset history --output history.csv
```

### Global Options

| Option | Default | Description |
|--------|---------|-------------|
| `--profile TEXT` | `default` | Profile name for data isolation |
| `--server-url TEXT` | `http://localhost:8420` | Server base URL |
| `--server / --no-server` | `--server` | Use server or direct mode |

### Example: Quick rate check (no server needed)

```bash
cryptotracker --no-server rate btc usd
```

### Example: Launch the server, then use the CLI

```bash
# Terminal 1 — start the server
cryptotracker server --port 8420

# Terminal 2 — run CLI commands
cryptotracker rate eth usd
cryptotracker convert btc rub 0.5
cryptotracker list-watch
```

### Example: Multiple profiles

```bash
cryptotracker --profile work rate usd eur
cryptotracker --profile personal rate btc usd
cryptotracker --profile personal history
```

### Help

```bash
cryptotracker --help            # Top-level help
cryptotracker rate --help       # Help for a specific command
```

---

## Architecture

```
┌──────────────────────┐       HTTP        ┌──────────────────────┐
│   CLI (Typer+Rich)   │ ───────────────→  │  Server (FastAPI)    │
│                      │ ←───────────────  │                      │
│  cryptotracker rate  │                   │  /api/rate           │
│  cryptotracker conv  │  ← fallback →     │  /api/convert        │
│  cryptotracker watch │    direct         │  /api/watch          │
│       ...            │    SQLite         │  ...                 │
└──────────────────────┘                   └──────────┬───────────┘
                                                      │
                                           ┌──────────▼───────────┐
                                           │  External APIs        │
                                           │  Frankfurter (fiat)   │
                                           │  CoinGecko  (crypto)  │
                                           └──────────────────────┘
```

- **Server mode** (default): CLI sends HTTP requests to the local FastAPI server.
  The server proxies external APIs and writes history to SQLite.
- **Direct mode** (`--no-server`): CLI calls external APIs directly and writes
  to the local SQLite database. Works without a running server.

---

## Server API

The FastAPI server exposes these endpoints (base: `http://localhost:8420/api`):

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/server/status` | Health check + external API status |
| `GET` | `/currencies` | List available fiat currencies |
| `GET` | `/crypto` | List available cryptocurrencies |
| `GET` | `/rate?base=X&target=Y` | Get exchange rate |
| `POST` | `/convert` | Convert amount between currencies |
| `GET` | `/history` | Request history with pagination |
| `POST` | `/watch` | Add pair to watchlist |
| `GET` | `/watch` | List watchlist with rates |
| `DELETE` | `/watch/{id}` | Remove pair from watchlist |
| `GET` | `/export` | Export data (JSON/CSV) |

Interactive API docs: http://localhost:8420/docs

---

## Project Structure

```
cryptotracker/
├── pyproject.toml              # Project metadata & dependencies
├── README.md                   # This file
├── tz.md                       # Technical specification (Russian)
├── .env.example                # Configuration template
├── .gitignore
│
├── cryptotracker/              # Python package root
│   ├── main.py                 # CLI entry point (Typer app)
│   ├── config.py               # Settings (pydantic-settings)
│   │
│   ├── cli/                    # CLI layer
│   │   ├── commands.py         # All 7 command implementations
│   │   ├── formatting.py       # Rich tables, panels, number formatting
│   │   └── errors.py           # Error handling helpers
│   │
│   ├── server/                 # Backend layer
│   │   ├── app.py              # FastAPI app, lifespan, CORS
│   │   ├── database.py         # Async SQLAlchemy engine & sessions
│   │   ├── models.py           # ORM models (5 tables)
│   │   ├── schemas.py          # Pydantic request/response schemas
│   │   └── routers/            # API route handlers
│   │       ├── rates.py        # /api/rate, /api/convert
│   │       ├── watchlist.py    # /api/watch (CRUD)
│   │       ├── history.py      # /api/history
│   │       ├── export.py       # /api/export
│   │       ├── currencies.py   # /api/currencies, /api/crypto
│   │       └── server_status.py # /api/server/status
│   │
│   └── api/                    # External API clients
│       ├── client.py           # httpx client with retry logic
│       ├── frankfurter.py      # Frankfurter API client
│       └── coingecko.py        # CoinGecko API client
│
├── tests/                      # Test suite (pytest)
│   ├── conftest.py             # Fixtures: temp DB, mocks, test client
│   ├── test_cli_commands.py    # CLI command tests (10)
│   └── test_api_endpoints.py   # API endpoint tests (12)
│
└── data/                       # Created automatically on first run
    └── cryptotracker.db        # SQLite database file
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `typer` | CLI framework |
| `rich` | Coloured terminal output |
| `httpx` | Async HTTP client |
| `fastapi` | REST API server |
| `uvicorn` | ASGI server |
| `sqlalchemy` | ORM + async SQLite |
| `aiosqlite` | Async SQLite driver |
| `pydantic` / `pydantic-settings` | Data validation & config |
| `python-dotenv` | `.env` file loading |

### Dev Dependencies

| Package | Purpose |
|---------|---------|
| `pytest` | Test framework |
| `pytest-asyncio` | Async test support |
| `pytest-httpx` | HTTP mocking (optional) |

---

## Testing

The project includes a comprehensive test suite with **22 tests** (10 CLI + 12 API).

### Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"
```

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Files

```bash
pytest tests/test_cli_commands.py -v
pytest tests/test_api_endpoints.py -v
```

### Test Coverage

| Area | Tests | What's Covered |
|------|-------|---------------|
| **CLI Commands** | 10 | `rate`, `convert`, `history`, `watch`, `list-watch`, `export` — validation errors, mocked API responses, empty states, duplicates |
| **API Endpoints** | 12 | `GET /api/server/status`, `GET /api/currencies`, `GET /api/rate`, `POST /api/convert`, `POST/GET/DELETE /api/watch`, `GET /api/history`, `GET /api/export` — 200/201/400/404/409/422 responses |

### Test Architecture

- **Isolated SQLite**: each test gets a temporary in-memory database via [`tests/conftest.py`](tests/conftest.py)
- **Mocked external APIs**: `FrankfurterClient` и `CoinGeckoClient` замоканы через `unittest.mock.AsyncMock`
- **No real server**: CLI-тесты используют `CliRunner` (direct mode), API-тесты — `httpx.ASGITransport`
- **Marker**: `@pytest.mark.anyio` для асинхронных API-тестов

---

## License

MIT License. See `pyproject.toml` for details.
