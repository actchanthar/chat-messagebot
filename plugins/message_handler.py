from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from database.database import db
from config import GROUP_CHAT_IDS
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message_text = update.message.text
    username = update.effective_user.username

    if chat_id not in GROUP_CHAT_IDS:
        logger.debug(f"Ignoring message from user {user_id} in non-approved chat {chat_id}")
        return

    if not await db.get_count_messages():
        logger.debug(f"Message counting disabled for user {user_id} in chat {chat_id}")
        return

    try:
        user = await db.get_user(user_id)
        if not user:
            user = await db.create_user(user_id, update.effective_user.full_name, username)
            if not user:
                logger.error(f"Failed to create user {user_id}")
                return

        if user.get("banned", False):
            logger.info(f"Ignoring message from banned user {user_id}")
            return

        if await db.check_rate_limit(user_id, message_text):
            logger.warning(f"Rate limit or duplicate message from user {user_id}")
            return

        group_messages = user.get("group_messages", {})
        group_messages[chat_id] = group_messages.get(chat_id, 0) + 1
        total_messages = user.get("messages", 0) + 1

        message_rate = await db.get_message_rate()  # e.g., 3 messages = 1 kyat
        balance_increment = 1 / message_rate
        new_balance = user.get("balance", 0) + balance_increment

        updates = {
            "group_messages": group_messages,
            "messages": total_messages,
            "balance": new_balance,
            "last_activity": datetime.utcnow(),
            "username": username
        }
        await db.update_user(user_id, updates)

        if new_balance >= 10 and not user.get("notified_10kyat", False):
            await update.message.reply_text("Congratulations! You've earned 10 kyat. Check with /balance.")
            await db.update_user(user_id, {"notified_10kyat": True})

        logger.info(f"Processed message from user {user_id} in chat {chat_id}: total_messages={total_messages}, balance={new_balance:.2f}, username={username}")
    except Exception as e:
        logger.error(f"Error processing message from user {user_id} in chat {chat_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))