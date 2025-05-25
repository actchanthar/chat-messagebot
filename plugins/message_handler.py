from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from database.database import db
import logging
from config import GROUP_CHAT_IDS, COUNT_MESSAGES, CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not COUNT_MESSAGES:
        logger.debug("Message counting disabled")
        return

    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Message from user {user_id} in chat {chat_id}")

    if chat_id not in GROUP_CHAT_IDS:
        logger.debug(f"Message in non-tracked chat {chat_id}")
        return

    user = await db.get_user(user_id)
    if not user:
        logger.info(f"User {user_id} not found, creating new user")
        user = await db.create_user(user_id, update.effective_user.full_name, None)
        if not user:
            logger.error(f"Failed to create user {user_id}")
            return

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned, ignoring message")
        return

    # Increment message count
    group_messages = user.get("group_messages", {})
    group_messages[chat_id] = group_messages.get(chat_id, 0) + 1
    total_messages = user.get("messages", 0) + 1

    # Calculate balance based on messages
    messages_per_kyat = await db.get_messages_per_kyat() or 1
    balance = total_messages / messages_per_kyat

    try:
        await db.update_user(user_id, {
            "messages": total_messages,
            "group_messages": group_messages,
            "balance": balance
        })
        logger.info(f"Updated user {user_id}: messages={total_messages}, balance={balance} {CURRENCY}")
    except Exception as e:
        logger.error(f"Error updating user {user_id} message count: {e}")

def register_handlers(application: Application):
    logger.info("Registering message handler")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Chat(GROUP_CHAT_IDS), handle_message))