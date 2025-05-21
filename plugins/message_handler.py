from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message_text = update.message.text

    if await db.check_rate_limit(user_id, message_text):
        return

    if not await db.get_count_messages():
        return

    if chat_id != "-1002061898677":
        return

    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name)

    message_rate = await db.get_message_rate()
    new_messages = user.get("messages", 0) + 1
    new_balance = user.get("balance", 0) + (1 / message_rate)
    group_messages = user.get("group_messages", {})
    group_messages[chat_id] = group_messages.get(chat_id, 0) + 1

    await db.update_user(user_id, {
        "messages": new_messages,
        "balance": new_balance,
        "group_messages": group_messages
    })
    logger.info(f"User {user_id} messages: {new_messages}, balance: {new_balance}")

def register_handlers(application: Application):
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))