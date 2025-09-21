from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import logging
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Now import what we need
from database.database import db
from utils.spam_detector import spam_detector
from config import APPROVED_GROUPS, LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle group messages for earning and spam detection"""
    if not update.message or not update.message.text:
        return
    
    user_id = str(update.effective_user.id)
    group_id = str(update.effective_chat.id)
    message_text = update.message.text
    
    try:
        # Check if group is approved
        if group_id not in APPROVED_GROUPS:
            return
        
        # Get or create user
        user = await db.get_user(user_id)
        if not user:
            user_name = {
                "first_name": update.effective_user.first_name or "",
                "last_name": update.effective_user.last_name or ""
            }
            user = await db.create_user(user_id, user_name)
            if not user:
                return
        
        # Check if user is banned
        if user.get("banned", False):
            try:
                await context.bot.ban_chat_member(group_id, user_id)
                await update.message.delete()
            except:
                pass
            return
        
        # Spam detection
        spam_result = await spam_detector.check_spam(
            message_text, 
            user.get("message_timestamps", []),
            user_id
        )
        
        if spam_result.get("is_spam", False):
            logger.warning(f"Spam detected from user {user_id}: {spam_result.get('reason')}")
            
            try:
                # Delete spam message
                await update.message.delete()
                
                # Increment spam count
                spam_count = user.get("spam_count", 0) + 1
                await db.update_user(user_id, {"spam_count": spam_count})
                
                # Ban after 3 spam messages
                if spam_count >= 3:
                    await context.bot.ban_chat_member(group_id, user_id)
                    await db.update_user(user_id, {"banned": True})
                    
                    # Notify admins
                    try:
                        await context.bot.send_message(
                            chat_id=LOG_CHANNEL_ID,
                            text=f"🚫 User {user_id} banned for spam in {group_id}\n"
                                 f"Reason: {spam_result.get('reason')}\n"
                                 f"Message: {message_text[:100]}..."
                        )
                    except:
                        pass
                
                return
            except Exception as e:
                logger.error(f"Failed to handle spam: {e}")
                return
        
        # Process message for earning
        earning_result = await db.process_message_earning(user_id, group_id)
        
        if earning_result.get("success", False):
            earning = earning_result.get("earning", 0)
            new_balance = earning_result.get("new_balance", 0)
            message_count = earning_result.get("message_count", 0)
            
            # Milestone notifications
            if earning > 0 and message_count % 100 == 0:
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"🎉 {message_count:,} messages sent! Balance: {int(new_balance)} kyat"
                    )
                except:
                    pass
    
    except Exception as e:
        logger.error(f"Error processing message: {e}")

def register_handlers(application: Application):
    """Register message handlers"""
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND, 
        handle_group_message
    ))
