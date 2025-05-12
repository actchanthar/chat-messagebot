# plugins/top.py
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import config
import logging

logger = logging.getLogger(__name__)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    logger.info(f"User {user_id} requested top users")

    top_users = await db.get_top_users()
    if not top_users:
        reply_text = "No top users found."
        if update.message:
            await update.message.reply_text(reply_text)
        elif update.callback_query:
            await update.callback_query.message.reply_text(reply_text)
        logger.info(f"No top users found for user {user_id}")
        return

    top_users_text = "ထိပ်တန်းအသုံးပြုသူ ၁၀ ဦး:\n"
    for i, user in enumerate(top_users, 1):
        top_users_text += f"{i}. {user['name']}: {user['messages']} စာတို၊ {user['balance']} {config.CURRENCY}\n"

    if update.message:
        await update.message.reply_text(top_users_text)
    elif update.callback_query:
        await update.callback_query.message.reply_text(top_users_text)
    logger.info(f"Sent top users to user {user_id}")

def register_handlers(application):
    logger.info("Registering top handlers")
    application.add_handler(CommandHandler("top", top))