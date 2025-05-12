# plugins/balance.py
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import config
import logging

logger = logging.getLogger(__name__)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    logger.info(f"User {user_id} requested balance")

    user = await db.get_user(user_id)
    if not user:
        if update.message:
            await update.message.reply_text("User not found. Please start with /start.")
        elif update.callback_query:
            await update.callback_query.message.reply_text("User not found. Please start with /start.")
        logger.error(f"User {user_id} not found in database")
        return

    balance = user.get("balance", 0)
    withdrawn_today = user.get("withdrawn_today", 0)
    reply_text = (
        f"Your balance is {balance} {config.CURRENCY}. 💰\n"
        f"Withdrawn today: {withdrawn_today} {config.CURRENCY}\n"
        f"သင့်လက်ကျန်ငွေပမာဏမှာ {balance} {config.CURRENCY} ဖြစ်ပါသည်။ 💰"
    )

    if update.message:
        await update.message.reply_text(reply_text)
    elif update.callback_query:
        await update.callback_query.message.reply_text(reply_text)
    logger.info(f"User {user_id} balance: {balance}")

def register_handlers(application):
    logger.info("Registering balance handlers")
    application.add_handler(CommandHandler("balance", balance))