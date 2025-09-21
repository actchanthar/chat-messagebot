from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
import logging
import sys
import os
import re

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import APPROVED_GROUPS, SPAM_KEYWORDS, SPAM_PATTERNS, MAX_EMOJI_COUNT, MAX_LINKS_COUNT, CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def is_spam_message(text: str) -> bool:
    """Check if message contains spam"""
    if not text:
        return False
    
    text_lower = text.lower()
    
    # Check spam keywords
    for keyword in SPAM_KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    
    # Check spam patterns
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    # Check excessive emojis
    emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', text))
    if emoji_count > MAX_EMOJI_COUNT:
        return True
    
    # Check excessive links
    link_count = len(re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text))
    if link_count > MAX_LINKS_COUNT:
        return True
    
    return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle group messages for earning system"""
    try:
        # Only process group messages
        if update.effective_chat.type not in ["group", "supergroup"]:
            return
        
        user_id = str(update.effective_user.id)
        group_id = str(update.effective_chat.id)
        message_text = update.message.text or ""
        
        # Check if group is approved for earning
        if group_id not in APPROVED_GROUPS:
            return
        
        # Get or create user
        user = await db.get_user(user_id)
        if not user:
            # Create new user automatically
            user = await db.create_user(user_id, {
                "first_name": update.effective_user.first_name,
                "last_name": update.effective_user.last_name
            })
            if not user:
                logger.error(f"Failed to create user {user_id} in message handler")
                return
        
        # Check if user is banned
        if user.get("banned", False):
            return
        
        # Check for spam
        if await is_spam_message(message_text):
            logger.info(f"Spam message detected from user {user_id}")
            return
        
        # Process message for earning - FIXED
        earned = await db.process_message_earning(user_id, group_id, context)
        
        if earned:
            # Get updated user data to show balance
            updated_user = await db.get_user(user_id)
            if updated_user:
                current_balance = updated_user.get("balance", 0)
                total_messages = updated_user.get("messages", 0)
                
                # Send earning notification
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"💰 **You earned 1 {CURRENCY}!**\n\n"
                             f"💳 **New Balance:** {int(current_balance)} {CURRENCY}\n"
                             f"📝 **Total Messages:** {total_messages:,}\n"
                             f"📊 **Rate:** 3 messages = 1 {CURRENCY}\n\n"
                             f"Keep chatting to earn more! 🚀"
                    )
                    logger.info(f"User {user_id} earned 1 {CURRENCY} in group {group_id}")
                except Exception as e:
                    logger.error(f"Failed to notify user {user_id} about earning: {e}")
        
        logger.debug(f"Processed message from user {user_id} in group {group_id}")
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")

def register_handlers(application: Application):
    """Register message handlers"""
    logger.info("Registering message handlers")
    
    # Handle all text messages in groups
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
        handle_message
    ))
    
    logger.info("✅ Message handlers registered successfully")
