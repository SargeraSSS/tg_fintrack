FinTrack 
A personal finance tracker you control entirely through Telegram — log expenses and income, track spending by category, and get a daily spending limit calculated automatically from your income, savings goal, and what you've already spent.

Telegram Bot  →  Django REST API  →  PostgreSQL

Features


Log expenses and income via chat
Monthly stats: spending by category, income, smart daily limit
Recurring payments, auto-logged monthly
Daily reminders (toggleable)
Multi-currency support (PLN, UAH, EUR, USD)
/help guide built into the bot


Tech stack

Backend: Django, Django REST Framework, PostgreSQL, Token auth
Bot: python-telegram-bot, httpx, APScheduler (background jobs)
Testing: pytest, pytest-django

Status

Active learning project. API, bot, and core features are done and tested. Docker + deployment planned next.