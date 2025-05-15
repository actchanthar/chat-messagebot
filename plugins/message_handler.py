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
    logger.info(f"Message received from user {user_id} in chat {chat_id}")

    # Check if message counting is enabled
    if not COUNT_MESSAGES:
        logger.info(f"Message counting is disabled. Skipping update in chat {chat_id}.")
        return

    # Check if the chat is in the admin-approved groups
    approved_groups = await db.get_approved_groups()
    if chat_id not in approved_groups:
        logger.info(f"Chat {chat_id} not in approved groups for counting. Skipping update.")
        return

    # Update message count and balance
    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name)

    # Update total messages
    new_messages = user.get("messages", 0) + 1
    new_balance = user.get("balance", 0) + 1  # 1 kyat per message

    # Update group-specific messages
    group_messages = user.get("group_messages", {})
    current_group_messages = group_messages.get(chat_id, 0) + 1
    group_messages[chat_id] = current_group_messages

    await db.update_user(user_id, {
        "messages": new_messages,
        "balance": new_balance,
        "group_messages": group_messages
    })
    logger.info(f"Updated messages to {new_messages} and balance to {new_balance} for user {user_id} in group {chat_id}")

def register_handlers(application: Application):
    logger.info("Registering message handlers")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))