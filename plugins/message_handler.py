from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from database.database import db
import logging
from config import COUNT_MESSAGES, GROUP_CHAT_IDS, CURRENCY
import random

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message_text = update.message.text
    logger.info(f"Message from user {user_id} in chat {chat_id}: {message_text}")

    try:
        if not COUNT_MESSAGES or chat_id not in GROUP_CHAT_IDS:
            return

        user = await db.get_user(user_id)
        if not user:
            user = await db.create_user(user_id, update.effective_user.full_name or "Unknown")
            logger.info(f"Created new user {user_id} in message handler")
            if not user:
                logger.error(f"Failed to create user {user_id}")
                return

        await db.update_user(user_id, {"username": update.effective_user.username})

        if user.get("banned", False):
            return

        if await db.check_rate_limit(user_id, message_text):
            return

        group_messages = user.get("group_messages", {})
        group_messages[chat_id] = group_messages.get(chat_id, 0) + 1
        total_messages = user.get("messages", 0) + 1
        balance = user.get("balance", 0)
        messages_per_kyat = await db.get_setting("messages_per_kyat", 3)

        if total_messages % messages_per_kyat == 0:
            balance += 1
            if balance >= 10 and not user.get("notified_10kyat", False):
                await update.message.reply_text(f"Congrats! You've earned {balance} {CURRENCY}. Keep chatting to earn more!")
                await db.update_user(user_id, {"notified_10kyat": True})

        updates = {
            "messages": total_messages,
            "group_messages": group_messages,
            "balance": balance,
            "last_activity": datetime.utcnow()
        }
        await db.update_user(user_id, updates)

        if random.random() < 0.01:
            await update.message.reply_text(f"You're earning {CURRENCY}! Keep chatting and check your balance with /balance.")
    except Exception as e:
        logger.error(f"Error in handle_message for user {user_id}: {e}", exc_info=True)

def register_handlers(application: Application):
    logger.info("Registering message handlers")
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message, block=False)
    )