# FinTrack — Learning Guide

A reference document covering everything built in this project. Updated as new concepts are introduced.

---

## 1. Project Architecture

```
Telegram Bot (bot.py)
        ↕ HTTP requests (httpx)
Django REST API (Django + DRF)
        ↕ ORM queries
PostgreSQL Database
```

**The flow in plain English:**
- The **Telegram bot** is the interface — the user only interacts with it
- The **Django API** is the brain — it handles all business logic and data
- **PostgreSQL** is the storage — all data lives here permanently

The bot never touches the database directly. It always goes through the API.

---

## 2. Project File Structure

```
fintrack/                   ← project root
├── fintrack/               ← Django project config
│   ├── settings.py         ← all project settings (DB, installed apps, etc.)
│   ├── urls.py             ← main URL router (connects to expenses/urls.py)
│   └── wsgi.py             ← production server entry point
├── expenses/               ← our Django app (the main logic)
│   ├── models.py           ← database table definitions
│   ├── serializers.py      ← convert Python objects ↔ JSON
│   ├── views.py            ← what happens when an API request comes in
│   ├── urls.py             ← URL routing for the expenses app
│   ├── admin.py            ← register models for the Django admin panel
│   └── migrations/         ← database migration history
├── bot.py                  ← Telegram bot code
├── .env                    ← secret keys and tokens (never commit to Git!)
└── manage.py               ← Django management command runner
```

---

## 3. Django Concepts

### Models (`models.py`)
A model = a database table. Each attribute = a column.

```python
class Expense(models.Model):
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)  # set automatically
    user = models.ForeignKey(User, on_delete=models.CASCADE)
```

**Field types used in this project:**
| Field | Use case |
|---|---|
| `CharField` | Short text (names, labels) |
| `DecimalField` | Money amounts |
| `DateField` | Dates |
| `IntegerField` | Whole numbers |
| `ForeignKey` | Link to another table (many-to-one) |
| `OneToOneField` | Link to another table (one-to-one) |
| `BigIntegerField` | Large numbers (e.g. Telegram IDs) |

**Key field options:**
- `blank=True, null=True` — field is optional
- `auto_now_add=True` — set to current date/time automatically on creation
- `unique=True` — no duplicates allowed
- `on_delete=models.CASCADE` — if parent is deleted, delete this too
- `choices=[...]` — restrict to a predefined list of values

### Migrations
Migrations sync your Python model definitions with the actual database.

```bash
python manage.py makemigrations   # Step 1: create a migration file (the plan)
python manage.py migrate          # Step 2: apply it to the database
```

**Types of migrations:**
- **Schema migration** — changes table structure (add/remove columns)
- **Data migration** — inserts or modifies data (e.g. default categories)

To create an empty data migration:
```bash
python manage.py makemigrations --empty expenses
```

---

## 4. Django REST Framework (DRF)

DRF is a library that makes building APIs with Django much easier.

### Serializers (`serializers.py`)
A serializer is a **translator** between Python objects and JSON.

```
Python object  →  Serializer  →  JSON   (sending data out)
JSON           →  Serializer  →  Python object  (receiving data in)
```

```python
class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ["id", "amount", "category", "date", "description", "user"]
        read_only_fields = ["user", "date"]  # can't be set manually
```

### ViewSets (`views.py`)
A ViewSet handles what happens when an API request comes in.

`ModelViewSet` gives you all 5 standard actions for free:
| Action | HTTP Method | URL |
|---|---|---|
| List all | GET | `/api/expenses/` |
| Create new | POST | `/api/expenses/` |
| Get one | GET | `/api/expenses/1/` |
| Update | PUT | `/api/expenses/1/` |
| Delete | DELETE | `/api/expenses/1/` |

```python
class ExpenseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]  # block unauthenticated requests
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        # return only THIS user's expenses
        return Expense.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # automatically attach the current user when saving
        serializer.save(user=self.request.user)
```

**Why `get_queryset` instead of `queryset`?**
`queryset` is evaluated once at startup and doesn't know who the current user is.
`get_queryset` is called per request, so `self.request.user` works correctly.

### Router (`urls.py`)
The Router automatically generates all URL patterns for registered ViewSets.

```python
router = routers.DefaultRouter()
router.register("expenses", ExpenseViewSet, basename="expense")
# generates: /api/expenses/, /api/expenses/1/, etc.
```

`basename` is required when you use `get_queryset` instead of `queryset`.

---

## 5. Authentication

### Token Authentication
How it works:
1. User sends username + password to `/api/token/`
2. API returns a token (a long random string)
3. Every future request includes: `Authorization: Token abc123...`
4. API reads the token and knows who the user is

**Analogy:** The token is like a building pass. You show your ID once (login) to get the pass (token). After that, you just show the pass at the door.

To enable token auth in `settings.py`:
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
}
```

### How users are created in this project
When a new Telegram user writes `/start`:
1. Bot sends POST to `/api/telegram-user/` with `telegram_id`
2. Django auto-creates a `User` with username `tg_123456789`
3. Django creates an auth token for that user
4. The token is returned in the response
5. Bot stores the token in `context.user_data['token']`
6. All future API calls use this token

---

## 6. Database Models Overview

| Model | Purpose |
|---|---|
| `Category` | Expense categories (Groceries, Rent, etc.) |
| `Expense` | Individual expense records |
| `UserProfile` | Per-user settings (currency, daily limit) |
| `RegularPayment` | Monthly recurring expenses |
| `TelegramUser` | Links a Telegram ID to a Django User |

**Relationships:**
```
User ──< Expense >── Category
User ── UserProfile
User ──< RegularPayment >── Category
User ── TelegramUser
```

---

## 7. Telegram Bot (`bot.py`)

### Key concepts

**Handlers** — functions that respond to specific events:
```python
app.add_handler(CommandHandler("start", start))         # responds to /start
app.add_handler(MessageHandler(filters.TEXT, handler))  # responds to any text
app.add_handler(CallbackQueryHandler(handler))          # responds to button presses
```

**`async/await`** — the bot is asynchronous. This means it can handle many users at the same time without waiting for one to finish.

```python
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello!")
```

**`context.user_data`** — a dictionary that stores data per user between messages:
```python
context.user_data['amount'] = 50.0   # store
amount = context.user_data.get('amount')  # retrieve
```

**Inline keyboard buttons:**
```python
keyboard = [[InlineKeyboardButton("Food 🍔", callback_data="1")]]
reply_markup = InlineKeyboardMarkup(keyboard)
await update.message.reply_text("Choose:", reply_markup=reply_markup)
```
When the user taps a button, `callback_data` is sent back to the bot.

### Making API requests from the bot
The bot uses `httpx` (async version of `requests`) to call the Django API:

```python
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{API_URL}/expenses/",
        json={"amount": 50.0, "category": 2},
        headers={"Authorization": f"Token {token}"}
    )
```

**Why `httpx` and not `requests`?**
`requests` is synchronous — it blocks the bot while waiting for a response.
`httpx` is async — the bot can keep handling other users while waiting.

---

## 8. Environment Variables (`.env`)

Secret values (tokens, passwords) should never be hardcoded in your source code.

`.env` file:
```
BOT_TOKEN=your_telegram_bot_token
ADMIN_TOKEN=your_django_admin_token
API_URL=http://127.0.0.1:8000/api
```

Loading in Python:
```python
from dotenv import load_dotenv
import os

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
```

**Always add `.env` to `.gitignore` — never commit secrets to Git.**

---

## 9. Tools Used

| Tool | Purpose |
|---|---|
| Django | Web framework, ORM, admin panel |
| Django REST Framework | Building the API |
| PostgreSQL | Production database |
| psycopg2-binary | Python driver for PostgreSQL |
| python-telegram-bot | Telegram bot library |
| httpx | Async HTTP requests |
| python-dotenv | Load `.env` files |
| pgAdmin 4 | GUI for managing PostgreSQL |
| Thunder Client | VS Code extension for testing APIs |

---

*This guide will be updated as new concepts are introduced.*
