from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from database.database import db
from config import GROUP_CHAT_IDS
import logging
from datetime import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message_text = update.message.text or "No text"
    username = update.effective_user.username or "None"
    name = update.effective_user.full_name or "Unknown"

    logger.info(f"Message received: user={user_id}, chat={chat_id}, text={message_text[:20]}...")

    if chat_id not in GROUP_CHAT_IDS:
        logger.info(f"Skipped: Chat {chat_id} not in GROUP_CHAT_IDS")
        return

    logger.info(f"count_messages check for user {user_id}")
    count_messages = await db.get_count_messages()
    logger.info(f"count_messages: {count_messages}")
    if not count_messages:
        logger.info(f"Skipped: Message counting disabled")
        return

    try:
        logger.info(f"Fetching user {user_id}")
        user = await db.get_user(user_id)
        if not user:
            logger.info(f"Creating user {user_id}")
            user = await db.create_user(user_id, name, username)
            if not user:
                logger.error(f"Failed to create user {user_id}")
                return
            logger.info(f"Created user {user_id}")

        if user.get("banned", False):
            logger.info(f"Skipped: User {user_id} is banned")
            return

        logger.info(f"Updating message count for user {user_id}")
        group_messages = user.get("group_messages", {})
        group_messages[chat_id] = group_messages.get(chat_id, 0) + 1
        total_messages = user.get("messages", 0) + 1
        message_rate = await db.get_message_rate()  # Should be 1
        # Calculate message-based balance increment
        message_balance = total_messages / message_rate
        # Preserve existing balance bonuses (e.g., from /add_bonus)
        current_balance = user.get("balance", 0)
        bonus_balance = max(0, current_balance - (user.get("messages", 0) / message_rate))
        new_balance = message_balance + bonus_balance

        updates = {
            "group_messages": group_messages,
            "messages": total_messages,
            "balance": new_balance,
            "last_activity": datetime.utcnow(),
            "username": username,
            "name": name
        }
        logger.info(f"Updating user {user_id} with: {updates}")
        success = await db.update_user(user_id, updates)
        if success:
            logger.info(f"Success: User {user_id} updated: messages={total_messages}, balance={new_balance:.2f}")
        else:
            logger.error(f"Failed to update user {user_id}")

    except Exception as e:
        logger.error(f"Error processing message for user {user_id} in chat {chat_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_handler))