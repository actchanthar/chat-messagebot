from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /Add_bonus <user_id> <amount>")
        return

    target_user_id, amount = context.args
    try:
        amount = int(amount)
        if amount <= 0:
            await update.message.reply_text("Amount must be positive.")
            return
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a number.")
        return

    if await db.add_bonus(target_user_id, amount):
        await update.message.reply_text(f"Added {amount} kyat bonus to user {target_user_id}.")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin added {amount} kyat bonus to user {target_user_id}."
        )
        await context.bot.send_message(
            chat_id=target_user_id,
            text