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
    logger.info(f"Message from {user_id} in {chat_id}: {message_text}")

    if not COUNT_MESSAGES or chat_id != "-1002061898677":
        return

    if await db.check_rate_limit(user_id, message_text):
        return

    user = await db.get_user(user_id) or await db.create_user(user_id, update.effective_user.full_name)
    messages = user.get("messages", 0) + 1
    group_messages = user.get("group_messages", {})
    group_messages[chat_id] = group_messages.get(chat_id, 0) + 1
    balance = user.get("balance", 0)
    message_rate = await db.get_setting("message_rate", 3)  # Default: 3 messages = 1 kyat
    if messages % message_rate == 0:
        balance += 1
        logger.info(f"Balance increased to {balance} for {user_id}")

    await db.update_user(user_id, {
        "messages": messages,
        "balance": balance,
        "group_messages": group_messages
    })
    logger.info(f"Updated {user_id}: messages={messages}, balance={balance}")

def register_handlers(application: Application):
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))