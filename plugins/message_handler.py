from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    message_text = update.message.text
    logger.info(f"Message received from user {user_id} in chat {chat_id}: {message_text}")

    # Only process messages in the specific group chat
    if chat_id != -1002061898677:
        return

    # Check rate limit
    try:
        rate_limit_ok = await db.check_rate_limit(user_id, "send_message")
        if not rate_limit_ok:
            logger.info(f"User {user_id} rate limited for sending messages")
            return  # Silently ignore if rate-limited
    except Exception as e:
        logger.error(f"Error checking rate limit for user {user_id}: {e}")
        return  # Silently ignore to avoid error message in group

    user = await db.get_user(user_id)
    if not user:
        logger.warning(f"User {user_id} not found in database")
        return

    # Update message count
    current_messages = user.get("group_messages", {}).get(str(chat_id), 0)
    new_messages = current_messages + 1
    balance = user.get("balance", 0)
    new_balance = balance + (new_messages // 3)  # 3 messages = 1 kyat

    await db.update_user(
        user_id,
        {
            f"group_messages.{chat_id}": new_messages,
            "balance": new_balance
        }
    )

    # Notify user if they earned 10 kyat
    if new_messages % 30 == 0:  # 30 messages = 10 kyat
        await context.bot.send_message(
            chat_id,
            f"🎉 {update.effective_user.full_name} earned 10 kyat! Total balance: {new_balance} kyat"
        )

    logger.info(f"Updated user {user_id} message count to {new_messages}, balance to {new_balance}")

def register_handlers(application: Application):
    logger.info("Registering message handlers")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))