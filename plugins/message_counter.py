from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
from database.database import db
import logging
from config import GROUP_CHAT_IDS, COUNT_MESSAGES, CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def count_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not COUNT_MESSAGES:
        logger.info("Message counting disabled")
        return

    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Counting message from user {user_id} in chat {chat_id}")

    if chat_id not in GROUP_CHAT_IDS:
        logger.debug(f"Non-tracked chat {chat_id}")
        return

    user = await db.get_user(user_id)
    if not user:
        logger.info(f"Creating user {user_id}")
        user = await db.create_user(user_id, update.effective_user.full_name, None)
        if not user:
            logger.error(f"Failed to create user {user_id}")
            return

    total_messages = user.get("messages", 0) + 1
    balance = total_messages  # 1 message = 1 kyat

    try:
        await db.update_user(user_id, {
            "messages": total_messages,
            "balance": balance
        })
        logger.info(f"User {user_id} updated: messages={total_messages}, balance={balance} {CURRENCY}")
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    logger.info(f"Chat ID: {chat_id}")
    await update.message.reply_text(f"Chat ID: {chat_id}")

def register_handlers(application: Application):
    logger.info("Registering message counter")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Chat(GROUP_CHAT_IDS), count_message))
    application.add_handler(CommandHandler("getchatid", get_chat_id))