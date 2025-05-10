from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes
from telegram.error import RetryAfter
from database.database import db
import logging

logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return
    
    user_id = str(update.effective_user.id)
    message_text = update.message.text or update.message.caption or ""
    if not message_text:
        return
    
    user = await db.get_user(user_id)
    if not user:
        await db.create_user(user_id, update.effective_user.first_name)
    
    if await db.is_spam(user_id, message_text):
        logger.info(f"Spam detected from user {user_id}: {message_text}")
        return  # Silently ignore spam instead of replying
    
    await db.increment_message(user_id, update.effective_user.first_name, message_text)

def register_handlers(application):
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.CAPTION & ~filters.COMMAND, handle_message))