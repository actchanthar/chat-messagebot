# plugins/message_handler.py
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
    message_text = update.message.text or update.message.caption
    if not message_text:
        return

    logger.info(f"Message from user {user_id} in chat {chat_id}: {message_text}")

    if await db.check_rate_limit(user_id, message_text):
        logger.warning(f"Rate limit or duplicate for user {user_id}")
        return

    if not COUNT_MESSAGES:
        logger.info(f"Message counting disabled")
        return

    if chat_id != "-1002061898677":
        logger.info(f"Chat {chat_id} is not the target group")
        return

    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name)

    settings = await db.get_settings()
    messages_per_kyat = settings.get("messages_per_kyat", 3)

    new_messages = user.get("messages", 0) + 1
    group_messages = user.get("group_messages", {})
    current_group_messages = group_messages.get(chat_id, 0) + 1
    group_messages[chat_id] = current_group_messages
    new_balance = user.get("balance", 0) + (1 / messages_per_kyat)

    await db.update_user(user_id, {
        "messages": new_messages,
        "balance": new_balance,
        "group_messages": group_messages,
        "last_activity": datetime.utcnow()
    })
    logger.info(f"User {user_id} messages: {new_messages}, balance: {new_balance} in group {chat_id}")

def register_handlers(application: Application):
    logger.info("Registering message handlers")
    application.add_handler(MessageHandler(filters.TEXT | filters.CAPTION & ~filters.COMMAND, handle_message))