from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import ADMIN_IDS, LOG_CHANNEL_ID
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"/users command initiated by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Only admins can delete failed broadcast users.")
        logger.info(f"User {user_id} attempted /users but is not an admin")
        return

    deleted_count = db.delete_failed_broadcast_users()
    message = f"Successfully deleted {deleted_count} users with failed broadcasts."

    try:
        await update.message.reply_text(message)
        logger.info(f"Deleted {deleted_count} failed broadcast users by user {user_id}")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin {user_id} deleted {deleted_count} failed broadcast users."
        )
    except Exception as e:
        logger.error(f"Failed to send /users response to user {user_id}: {e}")
        try:
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Failed to send /users response to {user_id}: {e}"
            )
        except Exception as log_error:
            logger.error(f"Failed to log /users error to {LOG_CHANNEL_ID}: {log_error}")

def register_handlers(application: Application):
    logger.info("Registering users handlers")
    application.add_handler(CommandHandler("users", users))