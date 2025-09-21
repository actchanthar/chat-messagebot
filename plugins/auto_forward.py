from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
import logging
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config import (
    RECEIPT_CHANNEL_ID,
    GENERAL_ANNOUNCEMENT_GROUPS,
    BOT_TOKEN
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoForwardSystem:
    def __init__(self):
        self.enabled = True
        logger.info("Auto-forward system initialized")

    async def should_forward_message(self, message) -> bool:
        """Check if message should be forwarded"""
        try:
            # Only forward messages that contain withdrawal proof keywords
            if not message.text:
                return False
            
            withdrawal_keywords = [
                "WITHDRAWAL SUCCESSFUL",
                "just received",
                "kyat!",
                "#Withdrawal",
                "#Success",
                "#RealPayments"
            ]
            
            text = message.text.upper()
            return any(keyword.upper() in text for keyword in withdrawal_keywords)
            
        except Exception as e:
            logger.error(f"Error checking if should forward: {e}")
            return False

async def handle_receipt_channel_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle messages from receipt channel and forward to groups"""
    try:
        message = update.message
        if not message:
            return
        
        chat_id = str(message.chat.id)
        
        # Only process messages from receipt channel
        if chat_id != str(RECEIPT_CHANNEL_ID):
            return
        
        # Check if this is a withdrawal receipt message
        auto_forward = AutoForwardSystem()
        if not await auto_forward.should_forward_message(message):
            logger.info("Message doesn't match forwarding criteria")
            return
        
        logger.info(f"Forwarding message from receipt channel {chat_id}")
        
        # Forward to all main groups
        forwarded_count = 0
        for group_id in GENERAL_ANNOUNCEMENT_GROUPS:
            try:
                # Forward the message to the group
                await context.bot.forward_message(
                    chat_id=group_id,
                    from_chat_id=RECEIPT_CHANNEL_ID,
                    message_id=message.message_id
                )
                
                forwarded_count += 1
                logger.info(f"✅ Message forwarded to group {group_id}")
                
                # Small delay to avoid spam limits
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Failed to forward to group {group_id}: {e}")
        
        if forwarded_count > 0:
            logger.info(f"✅ Successfully forwarded receipt to {forwarded_count} groups")
        
    except Exception as e:
        logger.error(f"Error in handle_receipt_channel_messages: {e}")

async def handle_manual_forward_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to manually forward a message"""
    user_id = str(update.effective_user.id)
    
    # Check admin permissions
    from config import ADMIN_IDS
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    try:
        # Check if replying to a message
        if not update.message.reply_to_message:
            await update.message.reply_text(
                "❌ **Invalid Usage**\n\n"
                "Reply to a message you want to forward to groups.\n"
                "**Example:** Reply to a withdrawal post with `/forward`"
            )
            return
        
        replied_message = update.message.reply_to_message
        
        # Forward to all main groups
        forwarded_count = 0
        for group_id in GENERAL_ANNOUNCEMENT_GROUPS:
            try:
                await context.bot.forward_message(
                    chat_id=group_id,
                    from_chat_id=update.effective_chat.id,
                    message_id=replied_message.message_id
                )
                
                forwarded_count += 1
                logger.info(f"✅ Manual forward to group {group_id}")
                
            except Exception as e:
                logger.error(f"❌ Failed manual forward to {group_id}: {e}")
        
        await update.message.reply_text(
            f"✅ **Message Forwarded**\n\n"
            f"Successfully forwarded to {forwarded_count} groups!"
        )
        
    except Exception as e:
        logger.error(f"Error in manual forward: {e}")
        await update.message.reply_text("❌ Error occurred while forwarding.")

def register_handlers(application: Application):
    """Register auto-forward handlers"""
    logger.info("Registering auto-forward handlers")
    
    # Handler for messages from receipt channel
    application.add_handler(MessageHandler(
        filters.Chat(chat_id=int(RECEIPT_CHANNEL_ID)) & filters.TEXT & ~filters.COMMAND,
        handle_receipt_channel_messages
    ))
    
    # Manual forward command for admins
    from telegram.ext import CommandHandler
    application.add_handler(CommandHandler("forward", handle_manual_forward_command))
    
    logger.info("✅ Auto-forward handlers registered successfully")
