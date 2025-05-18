from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from config import GROUP_CHAT_IDS
from database.database import db
import datetime
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Message received from user {user_id} in chat {chat_id}")

    if chat_id not in GROUP_CHAT_IDS:
        logger.info(f"Message from user {user_id} ignored: chat {chat_id} not in GROUP_CHAT_IDS")
        return

    user = db.get_user(user_id)
    if not user:
        logger.info(f"User {user_id} not found, creating new user")
        user = db.create_user(user_id, update.effective_user.full_name)

    if not db.check_rate_limit(user_id):
        logger.info(f"User {user_id} rate limited in chat {chat_id}")
        return

    # Update message timestamps
    timestamps = user.get("message_timestamps", [])
    timestamps.append(datetime.datetime.now())
    db.update_user(user_id, {"message_timestamps": timestamps})

    # Update group message count
    group_messages = user.get("group_messages", {})
    group_messages[chat_id] = group_messages.get(chat_id, 0) + 1
    db.update_user(user_id, {"group_messages": group_messages, "messages": user.get("messages", 0) + 1})

    logger.info(f"Updated message count for user {user_id} in chat {chat_id}")

def register_handlers(application: Application):
    logger.info("Registering message handler")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))