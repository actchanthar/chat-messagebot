from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
import logging
import sys
import os
import time
import re
from datetime import datetime, timedelta
from collections import defaultdict

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import (
    APPROVED_GROUPS, 
    CURRENCY, 
    ADMIN_IDS,
    SPAM_KEYWORDS,
    SPAM_PATTERNS,
    MAX_EMOJI_COUNT,
    MAX_MESSAGES_PER_MINUTE
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Gentle anti-spam tracking
user_message_times = defaultdict(list)
user_warnings = defaultdict(int)
user_last_message = {}

async def is_spam_message(message_text: str, user_id: str) -> tuple[bool, str, str]:
    """Gentle spam detection - returns (is_spam, reason, severity)"""
    if not message_text:
        return True, "Empty message", "mild"
    
    text = message_text.strip().lower()
    original_text = message_text.strip()
    
    # Check message length - more lenient
    if len(text) < 2:
        return True, "Message too short", "mild"
    
    if len(text) > 500:
        return True, "Message too long", "moderate"
    
    # Check for obvious spam patterns only
    obvious_spam_patterns = [
        r'^[a-z]{1,2}$',  # Only d, dm, etc.
        r'(.)\1{4,}',  # Only 5+ repeated characters (ddddd)
        r'^[^\w\s]*$',  # Only special characters
    ]
    
    for pattern in obvious_spam_patterns:
        if re.search(pattern, text):
            return True, f"Obvious spam pattern", "moderate"
    
    # Check against severe spam keywords only
    severe_spam = ["dmd", "dmmd", "dmdm", "mdm", "dm", "md", "rm", "em", "m", "g", "f", "k", "d"]
    
    if text in severe_spam:
        return True, f"Spam keyword: {text}", "moderate"
    
    # Rate limiting check - GENTLE
    now = time.time()
    user_times = user_message_times[user_id]
    
    # Remove old messages (older than 1 minute)
    user_times[:] = [t for t in user_times if now - t < 60]
    
    # Check if too many messages in last minute (increased limit)
    if len(user_times) >= MAX_MESSAGES_PER_MINUTE:
        return True, "Sending too fast", "mild"
    
    # Check for rapid messaging (less than 1 second apart)
    if user_id in user_last_message:
        time_diff = now - user_last_message[user_id]
        if time_diff < 1.0:  # Less than 1 second
            return True, "Messaging too rapidly", "rapid"
    
    # Update last message time
    user_last_message[user_id] = now
    user_times.append(now)
    
    return False, "", "none"

async def handle_spam_gently(update: Update, context: ContextTypes.DEFAULT_TYPE, reason: str, severity: str):
    """Gentle spam handling - Myanmar language"""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name or "သုံးစွဲသူ"
    
    # Delete the spam message silently
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
        logger.info(f"Deleted spam message from {user_id}: {reason} ({severity})")
    except:
        pass  # Ignore if can't delete
    
    # Handle different severity levels
    if severity == "rapid":
        # Just delay/ignore rapid messages - no warning
        logger.info(f"Rapid messaging from {user_id} - message ignored silently")
        return
    
    elif severity == "mild":
        # Very gentle warning - no punishment
        user_warnings[user_id] += 1
        warnings = user_warnings[user_id]
        
        if warnings <= 3:  # Only warn first 3 times
            warning_messages = [
                f"⏰ {user_name} - စာများကို ပိုနှေးနှေးပို့ပါ။ အဓိပ္পါယ်ရှိတဲ့စာများ ရေးပြီး ငွေရယူပါ! 💰",
                f"💬 {user_name} - ကောင်းသောစာများ ရေးပါ။ ရိုးရှင်းသောစာများဖြင့် ငွေရှာပါ! ({warnings}/3)",
                f"📝 {user_name} - အဓိပ္ပါယ်ပြည့်ဝသော စာများရေးပါ။ စပမ်မဟုတ်ဘဲ ငွေရှာပါ! ({warnings}/3)"
            ]
            warning_msg = warning_messages[min(warnings-1, 2)]
        else:
            return  # No more warnings after 3 times for mild spam
    
    elif severity == "moderate":
        # Moderate warning
        user_warnings[user_id] += 1
        warnings = user_warnings[user_id]
        
        if warnings <= 2:
            warning_msg = f"⚠️ {user_name} - စပမ်မလုပ်ပါနှင့်! အဓိပ္ပါယ်ရှိသော စာများရေးပြီး ငွေရယူပါ! ({warnings}/5)"
        elif warnings <= 4:
            warning_msg = f"🚨 {user_name} - စပမ်များလွန်းပါသည်! ကောင်းသောစာများ ရေးပါ! ({warnings}/5)"
        else:
            warning_msg = f"🔕 {user_name} - စပမ်များများလွန်းပါသည်! ၅မိနစ် ခဏစာရပ်ပါ။ ({warnings}/5)"
    
    else:
        return
    
    # Send gentle warning that auto-deletes
    try:
        warning = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=warning_msg
        )
        
        # Auto-delete warning after 8 seconds
        context.job_queue.run_once(
            lambda context: delete_warning_message(context, update.effective_chat.id, warning.message_id),
            8
        )
        
        logger.info(f"Sent gentle warning to {user_id}: {severity} - {warnings} warnings")
        
    except Exception as e:
        logger.error(f"Failed to send gentle warning: {e}")

def delete_warning_message(context, chat_id, message_id):
    """Helper to delete warning message"""
    try:
        context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gentle message handler - Myanmar friendly"""
    try:
        # Skip if not a text message
        if not update.message or not update.message.text:
            return
        
        # Skip if not in approved groups
        chat_id = str(update.effective_chat.id)
        if chat_id not in APPROVED_GROUPS:
            return
        
        # Skip if it's a command
        if update.message.text.startswith('/'):
            return
        
        user_id = str(update.effective_user.id)
        message_text = update.message.text
        
        # GENTLE SPAM CHECK
        is_spam, reason, severity = await is_spam_message(message_text, user_id)
        
        if is_spam:
            await handle_spam_gently(update, context, reason, severity)
            
            # Don't process earnings for spam, but be gentle about it
            if severity == "rapid":
                return  # Don't earn for rapid messages
            elif severity == "moderate":
                return  # Don't earn for obvious spam
            # For "mild" spam, still allow earning after first warning
        
        # Check if user has too many warnings (gentle cooldown)
        warnings = user_warnings.get(user_id, 0)
        if warnings >= 5:
            # Check if 5 minutes have passed since last warning
            now = time.time()
            if user_id in user_last_message:
                if now - user_last_message[user_id] < 300:  # 5 minutes
                    # Just ignore message during cooldown - no harsh action
                    try:
                        await context.bot.delete_message(
                            chat_id=update.effective_chat.id,
                            message_id=update.message.message_id
                        )
                    except:
                        pass
                    return
                else:
                    # Reset warnings after cooldown
                    user_warnings[user_id] = 0
                    logger.info(f"Reset warnings for user {user_id} after cooldown")
        
        # Get user from database
        user = await db.get_user(user_id)
        if not user:
            # Create user if doesn't exist
            user = await db.create_user(user_id, {
                "first_name": update.effective_user.first_name,
                "last_name": update.effective_user.last_name
            })
            if not user:
                return
        
        # Check if user is banned
        if user.get("banned", False):
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
            except:
                pass
            return
        
        # Process message for earning
        earned = await db.process_message_earning(user_id, chat_id, context)
        
        if earned:
            # User earned money - send Myanmar notification
            current_user = await db.get_user(user_id)
            new_balance = current_user.get("balance", 0) if current_user else 0
            
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"💰 သင် 1 {CURRENCY} ရရှိပါပြီ! လက်ကျန်ငွေ: {int(new_balance)} {CURRENCY}",
                    disable_notification=True
                )
                logger.info(f"User {user_id} earned 1 {CURRENCY} in group {chat_id}")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id} about earning: {e}")
    
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")

def register_handlers(application: Application):
    """Register gentle message handlers"""
    logger.info("Registering gentle message handlers with Myanmar language support")
    
    # Handle all text messages in groups (not commands)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
        handle_message
    ))
    
    logger.info("✅ Gentle message handlers registered successfully")
