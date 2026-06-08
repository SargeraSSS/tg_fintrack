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
    try:
        amount = float(text)
        context.user_data["amount"] = amount
        categories = await get_categories()
        keyboard = [
            [InlineKeyboardButton(cat["name"], callback_data=str(cat["id"]))]
            for cat in categories
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select category:", reply_markup=reply_markup)
    except ValueError:
        await update.message.reply_text("Please send a number 💸")


# getting the categories from API
async def get_categories():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_URL}/categories/", headers={"Authorization": f"Token {ADMIN_TOKEN}"}
        )
        return response.json()


async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category_id = int(query.data)
    amount = context.user_data.get("amount")
    token = context.user_data.get("token")
    # зберігаємо витрату в API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/expenses/",
            json={"amount": amount, "category": category_id},
            headers={"Authorization": f"Token {token}"},
        )

    if response.status_code == 201:
        await query.edit_message_text("✅ Expense saved!")
    else:
        await query.edit_message_text("❌ Something went wrong")


app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_category))
app.run_polling()
