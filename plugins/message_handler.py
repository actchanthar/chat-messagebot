from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes
from telegram.error import RetryAfter
from database.database import db
import logging
import config

# Set up logging
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle incoming messages, count them in registered groups, and notify users
    when they reach 10 kyat. Ignores private messages and non-text content.
    """
    # Log all updates to ensure the handler is triggered
    logger.info(f"Processing update in chat {update.effective_chat.id} (type: {update.effective_chat.type}), message: {update.message.text if update.message else 'None'}")

    if update.effective_chat.type == "private":
        logger.info(f"Private message received, ignoring for counting: {update.message.text}")
        return
    
    # Check if the group is registered for counting
    group_id = str(update.effective_chat.id)
    registered_groups = await db.get_groups()
    logger.info(f"Registered groups: {registered_groups}")
    if group_id not in registered_groups:
        logger.info(f"Group {group_id} not registered for message counting.")
        return
    
    # Get user and message details
    user_id = str(update.effective_user.id)
    message_text = update.message.text or update.message.caption or ""
    logger.info(f"Message from user {user_id} in group {group_id}: {message_text}")
    
    # Ignore messages without valid text
    if not message_text:
        logger.info(f"No valid text from user {user_id} in group {group_id}")
        return
    
    # Check if user exists in the database, create if not
    user = await db.get_user(user_id)
    if not user:
        logger.info(f"Creating new user {user_id}")
        await db.create_user(user_id, update.effective_user.first_name)
    
    # Check for spam
    if await db.is_spam(user_id, message_text):
        logger.info(f"Spam detected from user {user_id}: {message_text}")
        return  # Silently ignore spam
    
    # Increment message count and balance
    updated_user = await db.increment_message(user_id, update.effective_user.first_name, message_text)
    logger.info(f"Incremented messages for user {user_id} in group {group_id}. New count: {updated_user.get('messages', 0)}, Balance: {updated_user.get('balance', 0)}")
    
    # Check if user reached 10 kyat and hasn't been notified
    if updated_user.get("balance", 0) >= 10 and not updated_user.get("notified_10kyat", False):
        username = update.effective_user.username or update.effective_user.first_name
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"ဂုဏ်ယူပါတယ် @{username} ပိုက်ဆံ ၁၀ ကျပ်ရရှိပါပြီ ငွေထုတ်ရန် {config.WITHDRAWAL_THRESHOLD} ပြည့်ရင်ထုတ်လို့ရပါပြီ"
            )
            await db.mark_notified_10kyat(user_id)
            logger.info(f"Sent 10 kyat notification to {username} in group {group_id}")
        except RetryAfter as e:
            logger.warning(f"RetryAfter error: {e}")
        except Exception as e:
            logger.error(f"Error sending 10 kyat notification: {e}")

def register_handlers(application):
    """
    Register message handlers for text and captions, excluding commands.
    """
    logger.info("Registering message handlers")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.CAPTION & ~filters.COMMAND, handle_message))