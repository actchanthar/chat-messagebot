from telegram import Update
from telegram.ext import MessageHandler, filters, CallbackContext
import logging
from database import db

logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Process and count non-command messages."""
    # Skip messages sent in private chats
    if update.effective_chat.type == 'private':
        return
    
    user = update.effective_user
    user_id = str(user.id)
    message_text = update.message.text or update.message.caption or ""
    
    # Skip empty messages
    if not message_text:
        return
    
    # Record message in history
    await db.record_message(user_id, message_text)
    
    # Check for spam
    if await db.is_spam(user_id, message_text):
        # Don't count spam messages
        logger.info(f"Spam detected from user {user_id}: {message_text[:20]}...")
        return
    
    # Increment message count and balance
    await db.increment_user_message_count(user_id, user.first_name)

def register_handlers(application):
    """Register handlers for this plugin"""
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.CAPTION & ~filters.COMMAND, handle_message))