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


# getting the categories from API
async def get_categories():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_URL}/categories/", headers={"Authorization": f"Token {ADMIN_TOKEN}"}
        )
        return response.json()


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_URL}/stats/",
            headers={"Authorization": f"Token {context.user_data["token"]}"},
        )
        data = response.json()
        if response.status_code == 200:
            text = f"📊 {data['month']}\n\n"
            for cat in data["categories"]:
                text += f"{cat['category__name']} — {cat['total']} PLN\n"
            text += f"\n💰 Total: {data['total']} PLN"
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

    if response.status_code == 201:
        await query.edit_message_text(
            f"✅ Expense saved!\n"
            f"💰 Amount: {amount} PLN\n"
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
app.run_polling()
