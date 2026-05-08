# CourtBooker Bot

`CourtBooker Bot` is a production-style browser automation project that books sports courts at the moment slots open.  
It combines Telegram-based request intake, APScheduler timing precision, and Playwright browser automation with retry logic and rich logging.

## Why This Project Is Useful

Booking windows for popular courts often open at fixed times and fill in seconds.  
CourtBooker automates that workflow so users can send a natural-language request and let the bot execute the booking routine exactly when needed.

## Features

- Telegram booking intake (example: `Book Court 3 at 7pm on Saturday for 60 minutes`)
- Command UX: `/book`, `/status`, `/cancel <job_id>`
- Request parsing for court, weekday, time, and duration
- APScheduler-based execution at the exact parsed target slot time
- Playwright automation with realistic browser fingerprint settings
- Anti-detection basics (human-like delays, user-agent, headers, viewport)
- Retry loop for next available time window when a slot is unavailable
- Screenshot evidence for success/failure attempts
- Rich structured logs for local operations and debugging
- SQLite persistence for booking jobs and statuses
- Allure test reporting for richer test UI and history-ready artifacts
- GitHub Actions CI (flake8 + pytest + JUnit + Allure artifacts)

## Architecture

```text
Telegram User
   |
   v
telegram_handler.py  ---> parse_booking_message()
   |
   v
scheduler.py (APScheduler DateTrigger)
   |
   v
booking_engine.py (Playwright)
   |
   +--> success/failure screenshot -> artifacts/screenshots/
   |
   +--> callback message -> Telegram Bot API

settings.py / .env
   |
   +--> runtime config (URL, timezone, retries, user profile, DB path)

request_store.py (SQLite)
   |
   +--> persisted jobs (scheduled/running/confirmed/failed/cancelled)
```

## Project Layout

```text
bot/
  telegram_handler.py
  scheduler.py
  booking_engine.py
  request_store.py
config/
  settings.py
utils/
  logger.py
  captcha_handler.py
tests/
  fixtures/mock_booking_page.html
  test_booking_engine.py
  test_scheduler.py
  test_telegram_handler.py
.github/workflows/ci.yml
.env.example
requirements.txt
Dockerfile
docker-compose.yml
Makefile
scripts.ps1
main.py
README.md
```

## Setup

### 1) Clone and install

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

### 2) Configure environment

Copy `.env.example` to `.env` and fill values:

- `TELEGRAM_BOT_TOKEN`: token from BotFather
- `BOOKING_TARGET_URL`: target booking site (real or mock)
- `BOOKING_TIMEZONE`: booking timezone (default `Europe/London`)
- retry and identity fields for form submission

### 3) Telegram bot setup

1. Open [@BotFather](https://t.me/BotFather)
2. Run `/newbot`
3. Copy the token into `.env`
4. Message your bot once so `getUpdates` can receive chat updates

## Run Locally

```bash
python main.py
```

Send a message to your bot:

```text
/book Court 3 at 7pm on Saturday for 60 minutes
```

Bot confirmation:

```text
Got it - I'll attempt booking Court 3 at 07:00PM on Saturday. Job ID: <id>. I'll notify you once confirmed.
```

Check and control queued jobs:

```text
/status
/cancel <job_id>
```

`/status` returns each job with target time, current status, and ETA so you can verify real-time scheduling.

## Task Runner

- Linux/macOS via `Makefile`: `make setup`, `make run`, `make lint`, `make test`
- Windows PowerShell: `.\scripts.ps1 -Task setup`, `.\scripts.ps1 -Task run`

## Docker

```bash
docker compose up --build
```

The container persists screenshots/logs/SQLite state in `artifacts/`.

## Headless vs Visible Browser

- Headless mode (default): `BOOKING_HEADLESS=true`
- Visible mode for debugging: `BOOKING_HEADLESS=false`

## Testing

```bash
pytest
```

### Allure Reporting (Improved Test UI)

Generate Allure results:

```bash
pytest --clean-alluredir --alluredir=allure-results --junitxml=test-results.xml
```

Open interactive Allure UI locally:

```bash
allure serve allure-results
```

PowerShell helper commands:

```powershell
.\scripts.ps1 -Task test-allure
.\scripts.ps1 -Task allure-serve
```

> You need Allure CLI installed on your machine to render the HTML UI (`allure serve`).

Test coverage includes:

- message parsing and date/time extraction
- booking flow with Playwright route interception
- scheduler retry behavior and execution timing accuracy

## CI/CD Workflow

GitHub Actions workflow at `.github/workflows/ci.yml`:

- triggers on push/PR to `main`
- installs Python dependencies and Playwright Chromium
- runs `flake8`
- runs `pytest --junitxml=test-results.xml --alluredir=allure-results`
- uploads both JUnit XML and `allure-results` artifacts

## Tech Decisions

### Why Playwright over Selenium?

- Better auto-waiting and modern async web support
- More reliable handling of dynamic SPAs and JS-heavy UI
- Built-in network interception and trace/screenshot tooling
- Faster and cleaner API for robust bot workflows

### Scheduling choice

`APScheduler` provides precise run timing, durable job triggers, and clean retry orchestration for slot-open automation.

### Telegram integration approach

Direct Telegram Bot API usage (`getUpdates` + `sendMessage`) keeps deployment simple and dependency-light while still production-capable.

## CAPTCHA Handling Extension Point

`utils/captcha_handler.py` includes a dedicated integration seam for 2Captcha or similar providers.  
If your target site introduces reCAPTCHA/hCaptcha, plug provider API calls into `CaptchaSolver.solve()`.

## Portfolio Notes

To make this repository client-ready:

- keep screenshots from real successful bookings in `artifacts/screenshots/`
- add a short GIF of Telegram request -> confirmation
- include a short section in your proposal linking how retry logic handles high-demand slots

## Example Screenshots to Add

- `docs/telegram-request.png` (user booking message and bot confirmation)
- `docs/booking-success.png` (success state from Playwright run)
- `docs/booking-failure-retry.png` (failed attempt with retry notification)
