from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import LOG_CHANNEL_ID
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def checkgroup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"/checkgroup command initiated by user {user_id} in chat {chat_id}")

    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found. Please send a message in the group first.")
        logger.info(f"User {user_id} not found for /checkgroup")
        return

    required_channels = db.get_required_channels()
    subscribed_channels = user.get("subscribed_channels", [])

    missing_channels = [ch for ch in required_channels if ch not in subscribed_channels]
    if not missing_channels:
        message = "You are subscribed to all required groups!"
    else:
        message = f"Please join these groups:\n" + "\n".join(missing_channels)

    try:
        await update.message.reply_text(message)
        logger.info(f"Sent group check result to user {user_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send /checkgroup response to user {user_id}: {e}")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Failed to send /checkgroup response to {user_id}: {e}"
        )

def register_handlers(application: Application):
    logger.info("Registering checkgroup handlers")
    application.add_handler(CommandHandler("checkgroup", checkgroup))