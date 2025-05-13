# plugins/message_handler.py
from telegram import Update
from telegram.ext import MessageHandler, ContextTypes, filters
from database.database import db
import config
import logging
from datetime import datetime, timezone

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Registered groups for message counting
REGISTERED_GROUPS = ["-1002061898677", "-1002502926465"]
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)
    message = update.message.text

    logger.info(f"Processing update in chat {chat_id} (type: {update.effective_chat.type}), message: {message}")

    # Only process messages in registered groups
    if chat_id not in REGISTERED_GROUPS:
        logger.info(f"Group {chat_id} not registered for message counting.")
        return

    logger.info(f"Registered groups: {REGISTERED_GROUPS}")
    logger.info(f"Message from user {user_id} in group {chat_id}: {message}")

    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        return

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned, skipping message count")
        return

    # Spam detection: Check if the user sent a message in the last 10 seconds
    last_message_time = context.user_data.get("last_message_time")
    current_time = datetime.now(timezone.utc)
    if last_message_time and (current_time - last_message_time).total_seconds() < 10:
        logger.info(f"Spam detected from user {user_id}: {message}")
        return

    context.user_data["last_message_time"] = current_time

    # Increment message count and balance
    messages = user.get("messages", 0) + 1
    balance = user.get("balance", 0) + 1  # 1 message = 1 kyat
    success = await db.update_user(user_id, {"messages": messages, "balance": balance})

    if success:
        logger.info(f"Incremented messages for user {user_id} in group {chat_id}. New count: {messages}, Balance: {balance}")
    else:
        logger.error(f"Failed to update message count for user {user_id} in group {chat_id}")

def register_handlers(application):
    logger.info("Registering message handlers")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, message_handler))