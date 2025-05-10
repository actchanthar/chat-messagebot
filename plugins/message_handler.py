from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes
from telegram.error import RetryAfter
from database.database import db
import logging
import config

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
        return  # Silently ignore spam
    
    updated_user = await db.increment_message(user_id, update.effective_user.first_name, message_text)
    
    # Check if user reached 10 kyat and hasn't been notified
    if updated_user.get("balance", 0) >= 10 and not updated_user.get("notified_10kyat", False):
        username = update.effective_user.username or update.effective_user.first_name
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"ဂုဏ်ယူပါတယ် @{username} ပိုက်ဆံ ၁၀ ကျပ်ရရှိပါပြီ ငွေထုတ်ရန် {config.WITHDRAWAL_THRESHOLD} ပြည့်ရင်ထုတ်လို့ရပါပြီ"
            )
            await db.mark_notified_10kyat(user_id)
        except RetryAfter as e:
            logger.warning(f"RetryAfter error: {e}")
            # Skip notification to avoid flood control

def register_handlers(application):
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.CAPTION & ~filters.COMMAND, handle_message))