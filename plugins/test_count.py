from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
from config import ADMIN_IDS
import logging
from datetime import datetime  # Add this import

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.warning(f"Unauthorized /test_count attempt by user {user_id}")
        return

    try:
        user = await db.get_user(user_id)
        if not user:
            await update.message.reply_text("User not found.")
            logger.error(f"User {user_id} not found for /test_count")
            return

        group_messages = user.get("group_messages", {})
        group_messages["-1002061898677"] = group_messages.get("-1002061898677", 0) + 1
        total_messages = user.get("messages", 0) + 1
        message_rate = await db.get_message_rate()
        new_balance = total_messages / message_rate

        updates = {
            "group_messages": group_messages,
            "messages": total_messages,
            "balance": new_balance,
            "last_activity": datetime.utcnow()
        }
        success = await db.update_user(user_id, updates)
        if success:
            await update.message.reply_text(
                f"Manually counted 1 message.\n"
                f"Messages: {total_messages}\n"
                f"Balance: {new_balance:.2f} kyat"
            )
            logger.info(f"User {user_id} manually counted message: {updates}")
        else:
            await update.message.reply_text("Failed to count message.")
            logger.error(f"Failed to update user {user_id} for /test_count")
    except Exception as e:
        await update.message.reply_text("Error counting message.")
        logger.error(f"Error in /test_count for user {user_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("test_count", test_count))