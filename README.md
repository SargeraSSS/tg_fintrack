# FinTrack 💰

A personal finance tracker you control entirely through Telegram.

No app to install, no website to log into — you just message a bot, tell it how much you spent, pick a category, and it remembers everything for you.

## What it does

- **Track expenses** — send a number, pick a category, done. The bot stores it and confirms with the amount, category, and date.
- **Monthly stats** — see how much you've spent this month, broken down by category.
- **Expense history** — a simple list of everything you've logged this month.
- **Custom categories** — comes with a set of default categories (groceries, rent, subscriptions, etc.), but you can add or remove your own.
- **Recurring payments** — set up things like rent or internet once, and the bot logs them automatically on the day of the month you choose.
- **Daily reminders** — an optional nudge at 7 PM if you haven't logged anything that day. Can be turned off in settings.
- **Currency choice** — PLN, UAH, EUR, or USD.

## How it's built

The bot itself doesn't store anything — it's just the interface. All the actual logic and data live in a Django REST API:

```
Telegram Bot  →  Django REST API  →  PostgreSQL
```

When you send a message, the bot makes an HTTP request to the API, which reads or writes to the database and sends a response back. Each user is authenticated with their own token, so everyone only ever sees their own data.

Recurring payments and daily reminders run automatically in the background using a scheduler (APScheduler) — no manual triggering needed.

## Tech stack

- **Backend:** Django, Django REST Framework
- **Database:** PostgreSQL
- **Bot:** python-telegram-bot, httpx (async requests)
- **Scheduling:** APScheduler
- **Auth:** Token-based authentication

## Project status

This is an active learning project, built from scratch to practice backend development — REST API design, database modeling, authentication, and integrating a bot with a separate backend service.

**Done:**
- Full REST API (categories, expenses, user profiles, recurring payments)
- Token authentication
- Telegram bot with all core features above

**Planned next:**
- Automated tests (pytest)
- Docker setup
- Deployment to a VPS

## Why I built this

Wanted something more than a basic CRUD app — this has a separate API, a bot frontend, and background jobs that run automatically. Also just useful for tracking my own spending.