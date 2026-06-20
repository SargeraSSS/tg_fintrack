import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
import httpx
from telegram.ext import MessageHandler, filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
API_URL = os.getenv("API_URL")


start_message = """
👋 Welcome to FinTrack Bot!

I help you track your daily expenses easily right here in Telegram.

Here's what I can do:
💸 Record your expenses by simply sending a number
📊 Show your monthly spending stats
📋 Keep your expense history
🔄 Manage regular monthly payments
💰 Set a daily spending limit
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    status = await register_user(telegram_id, context)
    if status == 201:
        await update.message.reply_text(f"{start_message}")
    else:
        await update.message.reply_text("👋 Welcome back!")


async def register_user(telegram_id: int, context):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/telegram-user/",
            json={"telegram_id": telegram_id},
            headers={"Authorization": f"Token {ADMIN_TOKEN}"},
        )
        if response.status_code == 201:
            context.user_data["token"] = response.json()["token"]
        elif response.status_code == 400:
            # user already exists — fetch their token
            token_response = await client.get(
                f"{API_URL}/get-token/{telegram_id}/",
                headers={"Authorization": f"Token {ADMIN_TOKEN}"},
            )
            if token_response.status_code == 200:
                context.user_data["token"] = token_response.json()["token"]
        return response.status_code


# слухає повідомленя і перевіріяє чи це число
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not context.user_data.get("token"):
        telegram_id = update.effective_user.id
        await register_user(telegram_id, context)

    if not context.user_data.get("currency"):
        profile = await get_user_profile(context.user_data.get("token"))
        context.user_data["currency"] = profile["currency"]

    if context.user_data.get("state") == "adding_category":
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/categories/",
                json={"name": text},
                headers={"Authorization": f"Token {context.user_data['token']}"},
            )
        context.user_data["state"] = None
        if response.status_code == 201:
            await update.message.reply_text(f"✅ Category '{text}' added!")
        else:
            await update.message.reply_text("❌ Something went wrong")
        return
    elif context.user_data.get("state") == "adding_reg_name":
        context.user_data["reg_name"] = text
        context.user_data["state"] = "adding_reg_amount"
        await update.message.reply_text("💰 Enter payment amount:")
        return
    elif context.user_data.get("state") == "adding_reg_amount":
        context.user_data["reg_amount"] = float(text)
        context.user_data["state"] = "adding_reg_day"
        await update.message.reply_text("📅 Enter day of a mouth (1 - 31)")
        return
    elif context.user_data.get("state") == "adding_reg_day":
        day = int(text)
        if 1 <= day <= 31:
            context.user_data["reg_day"] = day
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_URL}/regular-payments/",
                    json={
                        "payment_day": context.user_data["reg_day"],
                        "amount": context.user_data["reg_amount"],
                        "name": context.user_data["reg_name"],
                        "category": context.user_data["reg_category_id"],
                    },
                    headers={"Authorization": f"Token {context.user_data['token']}"},
                )
            context.user_data["state"] = None
            if response.status_code == 201:
                await update.message.reply_text("✅ Regular payment added!")
            else:
                await update.message.reply_text("❌ Something went wrong")
        else:
            await update.message.reply_text("❌ Please enter a number between 1 and 31")
            return
    try:
        amount = float(text)
        context.user_data["amount"] = amount
        categories = await get_categories()
        keyboard = [
            [
                InlineKeyboardButton(
                    cat["name"], callback_data=f"{cat['id']}:{cat['name']}"
                )
            ]
            for cat in categories
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select category:", reply_markup=reply_markup)
    except ValueError:
        await update.message.reply_text("Please send a number 💸")


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("💱 Currency", callback_data="settings_currency"),
            InlineKeyboardButton("💰 Daily limit", callback_data="settings_limit"),
        ],
        [
            InlineKeyboardButton("📂 Categories", callback_data="settings_categories"),
            InlineKeyboardButton(
                "🔄 Regular payments", callback_data="settings_regular"
            ),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⚙️ Settings", reply_markup=reply_markup)


async def get_user_profile(token):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_URL}/get-profile/", headers={"Authorization": f"Token {token}"}
        )
        if response.status_code == 200:
            return response.json()
    return {"currency": "PLN", "day_limit": None}


# CURRENCY_CHOICES = [
#     ("PLN", "PLN zł"),
#     ("UAH", "UAH ₴"),
#     ("EUR", "EUR €"),
#     ("USD", "USD $"),
# ]


async def handle_settings_callback(query, context):
    if query.data == "settings_currency":
        keyboard = [
            [
                InlineKeyboardButton("PLN zł", callback_data="currency_PLN"),
                InlineKeyboardButton("UAH ₴", callback_data="currency_UAH"),
            ],
            [
                InlineKeyboardButton("EUR €", callback_data="currency_EUR"),
                InlineKeyboardButton("USD $", callback_data="currency_USD"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("💱 Choose currency:", reply_markup=reply_markup)
    elif query.data.startswith("currency_"):
        currency = query.data.split("_")[1]
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/set-currency/",
                json={"currency": currency},
                headers={"Authorization": f"Token {context.user_data['token']}"},
            )
        if response.status_code == 200:
            context.user_data["currency"] = currency
            await query.edit_message_text(f"✅ Currency set to {currency}!")
        else:
            await query.edit_message_text("❌ Something went wrong")
    elif query.data == "settings_limit":
        await query.edit_message_text("💰 Daily limit feature coming soon!")
    elif query.data == "settings_categories":
        keyboard = [
            [
                InlineKeyboardButton("➕ Add category", callback_data="cat_add"),
                InlineKeyboardButton("🗑 Delete category", callback_data="cat_delete"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📂 Categories:", reply_markup=reply_markup)
        pass
    elif query.data == "cat_add":
        context.user_data["state"] = "adding_category"
        await query.edit_message_text("✏️ Enter category name:")
    elif query.data == "cat_delete":
        categories = await get_categories()
        keyboard = [
            [
                InlineKeyboardButton(
                    f"🗑 {cat['name']}", callback_data=f"delete_{cat['id']}"
                )
            ]
            for cat in categories
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Select category to delete:", reply_markup=reply_markup
        )
    elif query.data.startswith("delete_"):
        category_id = query.data.split("_")[1]
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{API_URL}/categories/{category_id}/",
                headers={"Authorization": f"Token {context.user_data['token']}"},
            )
        if response.status_code == 204:
            await query.edit_message_text("✅ Category deleted!")
        else:
            await query.edit_message_text("❌ Something went wrong")
    elif query.data == "settings_regular":
        keyboard = [
            [
                InlineKeyboardButton("➕ Add payment", callback_data="reg_add"),
                InlineKeyboardButton("📋 View payments", callback_data="reg_view"),
            ],
            [InlineKeyboardButton("🗑 Delete payment", callback_data="reg_delete")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🔄 Regular payments:", reply_markup=reply_markup)
    elif query.data == "reg_add":
        categories = await get_categories()
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{cat['name']}", callback_data=f"regcat_{cat['id']}"
                )
            ]
            for cat in categories
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Select category for regular payment:", reply_markup=reply_markup
        )
    elif query.data.startswith("regcat_"):
        context.user_data["reg_category_id"] = query.data.split("_")[1]
        context.user_data["state"] = "adding_reg_name"
        await query.edit_message_text("✏️ Enter payment name (e.g. Internet):")


# getting the categories from API
async def get_categories():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_URL}/categories/", headers={"Authorization": f"Token {ADMIN_TOKEN}"}
        )
        return response.json()


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with httpx.AsyncClient() as client:
        currency = context.user_data.get("currency", "PLN")
        response = await client.get(
            f"{API_URL}/stats/",
            headers={"Authorization": f"Token {context.user_data["token"]}"},
        )
        data = response.json()
        if response.status_code == 200:
            text = f"📊 {data['month']}\n\n"
            for cat in data["categories"]:
                text += f"{cat['category__name']} — {cat['total']} {currency}\n"
            text += f"\n💰 Total: {data['total']} {currency}"
            await update.message.reply_text(text)


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with httpx.AsyncClient() as client:
        responce = await client.get(
            f"{API_URL}/history/",
            headers={"Authorization": f"Token {context.user_data["token"]}"},
        )
        data = responce.json()
        text = "📋 History\n\n"
        for expense in data:
            desc = f" — {expense['description']}" if expense["description"] else ""
            text += f"{expense['date']} — {expense['category__name']} — {expense['amount']} PLN{desc}\n"
        await update.message.reply_text(text)


async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if (
        query.data.startswith("settings_")
        or query.data.startswith("cat_")
        or query.data.startswith("delete_")
        or query.data.startswith("currency_")
        or query.data.startswith("reg_")
        or query.data.startswith("regcat_")
    ):
        await handle_settings_callback(query, context)
        return
    amount = context.user_data.get("amount")
    token = context.user_data.get("token")
    data = query.data.split(":")

    category_id = int(data[0])
    category_name = data[1]

    # зберігаємо витрату в API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/expenses/",
            json={"amount": amount, "category": category_id},
            headers={"Authorization": f"Token {token}"},
        )
    currency = context.user_data.get("currency", "PLN")
    if response.status_code == 201:
        await query.edit_message_text(
            f"✅ Expense saved!\n"
            f"💰 Amount: {amount} {currency} \n"
            f"📂 Category: {category_name}\n"
            f"📅 Date: {response.json()['date']}"
        )
    else:
        await query.edit_message_text(
            "💡 To record an expense, just send a number. Example: 100"
        )


#


app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_category))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("history", history))
app.add_handler(CommandHandler("settings", settings))
app.run_polling()
