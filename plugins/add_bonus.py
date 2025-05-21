from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
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
        if await db.add_bonus(target_user_id, amount):
            await update.message.reply_text(f"Added {amount} kyat bonus to user {target_user_id}.")
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"You received a {amount} kyat bonus from the admin!"
            )
            await context.bot.send_message(
                LOG_CHANNEL_ID,
                f"Admin added {amount} kyat bonus to user {target_user_id}."
            )
        else:
            await update.message.reply_text("Failed to add bonus. User not found.")
    except ValueError:
        await update.message.reply_text("Please provide a valid amount.")

def register_handlers(application):
    logger.info("Registering add_bonus handlers")
    application.add_handler(CommandHandler("Add_bonus", add_bonus))