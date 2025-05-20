from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from database.database import db
import logging
from config import COUNT_MESSAGES

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message_text = update.message.text
    logger.info(f"Message from user {user_id} in chat {chat_id}: {message_text}")

    try:
        if await db.check_rate_limit(user_id, message_text):
            return

        if not COUNT_MESSAGES:
            return

        if chat_id != "-1002061898677":
            return

        user = await db.get_user(user_id)
        if not user:
            user = await db.create_user(user_id, update.effective_user.full_name)

        messages_per_kyat = await db.get_setting("messages_per_kyat", 3)
        new_messages = user.get("messages", 0) + 1
        new_balance = user.get("balance", 0) + (1 if new_messages % messages_per_kyat == 0 else 0)
        group_messages = user.get("group_messages", {})
        group_messages[chat_id] = group_messages.get(chat_id, 0) + 1

        await db.update_user(user_id, {
            "messages": new_messages,
            "balance": new_balance,
            "group_messages": group_messages
        })
        logger.info(f"Updated user {user_id}: messages={new_messages}, balance={new_balance}")
    except Exception as e:
        logger.error(f"Error in handle_message for user {user_id}: {e}")

def register_handlers(application: Application):
    logger.info("Registering message handlers")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message, block=False))