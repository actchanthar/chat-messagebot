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

# Anti-spam tracking
user_message_times = defaultdict(list)
user_warnings = defaultdict(int)
user_cooldowns = {}

async def is_spam_message(message_text: str, user_id: str) -> tuple[bool, str]:
    """Enhanced spam detection"""
    if not message_text:
        return True, "Empty message"
    
    text = message_text.strip().lower()
    original_text = message_text.strip()
    
    # Check message length
    if len(text) < 3:
        return True, "Message too short"
    
    if len(text) > 500:
        return True, "Message too long"
    
    # Check for repeated characters (ddd, mmm, etc)
    if re.search(r'(.)\1{3,}', text):
        return True, "Too many repeated characters"
    
    # Check for spam patterns
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, text):
            return True, f"Matches spam pattern"
    
    # Check spam keywords
    for keyword in SPAM_KEYWORDS:
        if text == keyword.lower() or text in keyword.lower():
            return True, f"Spam keyword: {text}"
    
    # Check for excessive emojis
    emoji_count = len(re.findall(r'[^\w\s]', original_text))
    if emoji_count > MAX_EMOJI_COUNT:
        return True, "Too many emojis/special characters"
    
    # Rate limiting check
    now = time.time()
    user_times = user_message_times[user_id]
    
    # Remove old messages (older than 1 minute)
    user_times[:] = [t for t in user_times if now - t < 60]
    
    # Check if too many messages in last minute
    if len(user_times) >= MAX_MESSAGES_PER_MINUTE:
        return True, "Rate limit exceeded"
    
    # Add current message time
    user_times.append(now)
    
    return False, ""

async def handle_spam(update: Update, context: ContextTypes.DEFAULT_TYPE, reason: str):
    """Handle spam message with progressive punishment"""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name or "User"
    
    # Increase warning count
    user_warnings[user_id] += 1
    warnings = user_warnings[user_id]
    
    # Delete the spam message
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
        logger.info(f"Deleted spam message from {user_id}: {reason}")
    except Exception as e:
        logger.error(f"Failed to delete spam message: {e}")
    
    # Apply progressive punishment
    if warnings >= 5:
        # Ban user after 5 warnings
        await db.ban_user(user_id, f"Spam: {reason}")
        
        # Try to ban from group
        try:
            await context.bot.ban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=int(user_id)
            )
            warning_msg = f"🚫 {user_name} has been banned for excessive spam!"
        except Exception as e:
            warning_msg = f"🚫 {user_name} banned from bot for spam!"
            logger.error(f"Failed to ban from group: {e}")
        
    elif warnings >= 3:
        # Mute for 1 hour after 3 warnings
        user_cooldowns[user_id] = time.time() + 3600  # 1 hour
        warning_msg = f"🔇 {user_name} muted for 1 hour! (Warning {warnings}/5)\nStop spamming or you'll be banned!"
        
    else:
        # Just warn and cooldown
        user_cooldowns[user_id] = time.time() + 300  # 5 minutes cooldown
        warning_msg = f"⚠️ {user_name}: No spam allowed! (Warning {warnings}/5)\nWrite meaningful messages to earn!"
    
    # Send warning message that auto-deletes
    try:
        warning = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=warning_msg
        )
        
        # Auto-delete warning after 15 seconds
        def delete_warning():
            try:
                context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=warning.message_id
                )
            except:
                pass
        
        context.job_queue.run_once(
            lambda context: delete_warning(),
            15
        )
    except Exception as e:
        logger.error(f"Failed to send warning: {e}")
    
    logger.warning(f"Spam detected from {user_id}: {reason} (Warning {warnings}/5)")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced message handler with anti-spam and earning system"""
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
        
        # CHECK FOR SPAM FIRST
        is_spam, reason = await is_spam_message(message_text, user_id)
        if is_spam:
            await handle_spam(update, context, reason)
            return  # Don't process earnings for spam
        
        # Check if user is in cooldown
        if user_id in user_cooldowns:
            if time.time() < user_cooldowns[user_id]:
                # User is in cooldown, delete message silently
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=update.message.message_id
                    )
                except:
                    pass
                return
            else:
                # Cooldown expired
                del user_cooldowns[user_id]
        
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
            # User earned money - send notification
            current_user = await db.get_user(user_id)
            new_balance = current_user.get("balance", 0) if current_user else 0
            
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"💰 You earned 1 {CURRENCY}! New balance: {int(new_balance)} {CURRENCY}",
                    disable_notification=True
                )
                logger.info(f"User {user_id} earned 1 {CURRENCY} in group {chat_id}")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id} about earning: {e}")
    
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")

def register_handlers(application: Application):
    """Register message handlers"""
    logger.info("Registering message handlers")
    
    # Handle all text messages in groups (not commands)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
        handle_message
    ))
    
    logger.info("✅ Message handlers registered successfully")
