from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from database.database import db
import logging
from config import COUNT_MESSAGES, GROUP_CHAT_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Message received from user {user_id} in chat {chat_id}")

    # Check if message counting is enabled and if the chat is in GROUP_CHAT_IDS
    if not COUNT_MESSAGES or str(chat_id) not in GROUP_CHAT_IDS:
        logger.info(f"Message counting is disabled or chat {chat_id} not in GROUP_CHAT_IDS. Skipping update.")
        return

    # Update message count and balance (e.g., 1 kyat per message)
    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name)

    new_messages = user.get("messages", 0) + 1
    new_balance = user.get("balance", 0) + 1  # Assuming 1 kyat per message
    await db.update_user(user_id, {
        "messages": new_messages,
        "balance": new_balance
    })
    logger.info(f"Updated messages to {new_messages} and balance to {new_balance} for user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering message handlers")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))