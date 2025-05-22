from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
from config import ADMIN_IDS
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.warning(f"Unauthorized /debug_count attempt by user {user_id}")
        return

    try:
        count_messages = await db.get_count_messages()
        user = await db.get_user(user_id)
        group_messages = user.get("group_messages", {}).get("-1002061898677", 0) if user else 0
        total_messages = user.get("messages", 0) if user else 0
        message_rate = await db.get_message_rate()
        balance = user.get("balance", 0) if user else 0

        message = (
            f"Debug Message Counting:\n"
            f"count_messages: {count_messages}\n"
            f"Group (-1002061898677) messages: {group_messages}\n"
            f"Total messages: {total_messages}\n"
            f"Message rate: {message_rate} msg/kyat\n"
            f"Balance: {balance:.2f} kyat\n"
            f"Send a message in -1002061898677 and re-run to test."
        )
        await update.message.reply_text(message)
        logger.info(f"User {user_id} ran /debug_count")
    except Exception as e:
        await update.message.reply_text("Failed to debug message counting.")
        logger.error(f"Error in /debug_count for user {user_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("debug_count", debug_count))