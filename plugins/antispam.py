import re
import time
from datetime import datetime, timedelta
from collections import defaultdict
from telegram import Update
from telegram.ext import ContextTypes
import logging

# User message tracking
user_message_times = defaultdict(list)
user_warnings = defaultdict(int)
user_cooldowns = {}

logger = logging.getLogger(__name__)

async def is_spam_message(message_text: str, user_id: str) -> tuple[bool, str]:
    """Enhanced spam detection"""
    if not message_text:
        return True, "Empty message"
    
    text = message_text.strip().lower()
    
    # Check message length
    if len(text) < 3:
        return True, "Message too short"
    
    if len(text) > 500:
        return True, "Message too long"
    
    # Check for repeated characters
    if re.search(r'(.)\1{3,}', text):
        return True, "Too many repeated characters"
    
    # Check for spam patterns
    spam_patterns = [
        r'^[a-z]{1,3}$',  # d, dm, dmd
        r'^(ha|haha|lol|wtf|omg|bruh|ok|yes|no)$',
        r'(.{1,3})\1{2,}',  # dmdmdm
        r'^[^\w\s]*$',  # Only special characters
    ]
    
    for pattern in spam_patterns:
        if re.search(pattern, text):
            return True, f"Matches spam pattern: {pattern}"
    
    # Check spam keywords
    spam_keywords = [
        "dmd", "dmmd", "dmdm", "mdm", "dm", "md", "rm", "em",
        "gm", "fkf", "kf", "mdfof", "rrkrek"
    ]
    
    if text in spam_keywords:
        return True, f"Spam keyword: {text}"
    
    # Check rate limiting
    now = time.time()
    user_times = user_message_times[user_id]
    
    # Remove old messages (older than 1 minute)
    user_times[:] = [t for t in user_times if now - t < 60]
    
    # Check if too many messages in last minute
    if len(user_times) >= 10:
        return True, "Rate limit exceeded"
    
    # Add current message time
    user_times.append(now)
    
    return False, ""

async def handle_spam(update: Update, context: ContextTypes.DEFAULT_TYPE, reason: str):
    """Handle spam message"""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name or "User"
    group_id = str(update.effective_chat.id)
    
    # Increase warning count
    user_warnings[user_id] += 1
    warnings = user_warnings[user_id]
    
    # Delete the spam message
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except:
        pass  # May not have permission
    
    # Apply progressive punishment
    if warnings >= 5:
        # Ban user after 5 warnings
        from database.database import db
        await db.ban_user(user_id, f"Spam: {reason}")
        
        # Try to ban from group
        try:
            await context.bot.ban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=int(user_id)
            )
        except:
            pass
        
        warning_msg = f"🚫 {user_name} has been banned for excessive spam!"
        
    elif warnings >= 3:
        # Mute for 1 hour after 3 warnings
        until_date = datetime.now() + timedelta(hours=1)
        try:
            await context.bot.restrict_chat_member(
                chat_id=update.effective_chat.id,
                user_id=int(user_id),
                until_date=until_date,
                permissions=ChatPermissions(can_send_messages=False)
            )
        except:
            pass
        
        user_cooldowns[user_id] = time.time() + 3600  # 1 hour
        warning_msg = f"🔇 {user_name} muted for 1 hour! (Warning {warnings}/5)"
        
    else:
        # Just warn
        user_cooldowns[user_id] = time.time() + 300  # 5 minutes cooldown
        warning_msg = f"⚠️ {user_name}: No spam! (Warning {warnings}/5)"
    
    # Send warning message
    try:
        warning = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=warning_msg
        )
        # Auto-delete warning after 10 seconds
        context.job_queue.run_once(
            lambda context: context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=warning.message_id
            ),
            10
        )
    except:
        pass
    
    logger.warning(f"Spam detected from {user_id} in {group_id}: {reason}")
