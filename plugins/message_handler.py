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
    MEANINGFUL_PATTERNS,
    MAX_EMOJI_COUNT,
    MAX_MESSAGES_PER_MINUTE,
    RAPID_MESSAGE_THRESHOLD,
    MAX_RAPID_MESSAGES,
    RAPID_WINDOW_SECONDS,
    MAX_MESSAGES_IN_WINDOW,
    PROTECT_NORMAL_USERS,
    SMART_SPAM_DETECTION,
    DETAILED_SPAM_LOGGING,
    LOG_NORMAL_USERS,
    LOG_EARNING_NOTIFICATIONS
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Smart anti-spam tracking - separate tracking for different types
user_message_times = defaultdict(list)
user_rapid_count = defaultdict(int)
user_last_message = {}
user_warning_count = defaultdict(int)
user_last_warning_reset = defaultdict(float)

def is_meaningful_message(message_text: str) -> tuple[bool, str]:
    """Smart detection for meaningful messages (normal users)"""
    if not message_text:
        return False, "Empty message"
    
    text = message_text.strip()
    
    # Check against meaningful patterns from config
    for pattern in MEANINGFUL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True, f"Matched meaningful pattern: {pattern[:20]}..."
    
    # Additional smart checks
    
    # Length check - longer messages are usually meaningful
    if len(text) >= 10:
        return True, "Message length >= 10 characters"
    
    # Multiple words check
    words = text.split()
    if len(words) >= 2:
        # Check if words are not just repeated letters
        unique_words = set(word.lower() for word in words if len(word) > 1)
        if len(unique_words) >= 2:
            return True, "Multiple unique words"
    
    # Myanmar script detection
    myanmar_chars = len(re.findall(r'[\u1000-\u109F]', text))
    if myanmar_chars >= 2:
        return True, "Contains Myanmar text"
    
    # Numbers and mixed content
    has_numbers = bool(re.search(r'\d', text))
    has_letters = bool(re.search(r'[a-zA-Z]', text))
    if has_numbers and has_letters:
        return True, "Mixed numbers and letters"
    
    # Common conversation patterns
    conversation_patterns = [
        r'(good|morning|evening|night|hello|hi|hey|thanks|thank you|bye|see you)',
        r'(how|what|when|where|why|who).{0,20}[?]',
        r'(yes|no|ok|okay|sure|maybe|really|wow|cool|nice)',
        r'[0-9]+\s*(am|pm|hour|minute|day|week|month|year)',
    ]
    
    for pattern in conversation_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True, f"Conversation pattern: {pattern[:20]}..."
    
    return False, "No meaningful patterns detected"

def is_obvious_spam(message_text: str) -> tuple[bool, str]:
    """Detection for obvious spam only - very restrictive"""
    if not message_text:
        return True, "Empty message"
    
    text = message_text.strip().lower()
    
    # Check against spam patterns from config
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, text):
            return True, f"Matched spam pattern: {pattern}"
    
    # Check against spam keywords from config  
    if text in SPAM_KEYWORDS:
        return True, f"Spam keyword: {text}"
    
    # Very obvious spam patterns
    obvious_patterns = [
        r'^[a-z]{1,2}$',      # Only d, dm, dmd
        r'(.)\1{5,}',         # 6+ repeated chars (dddddd)
        r'^[^\w\s]*$',        # Only symbols (!@#$)
        r'^[a-z]\s[a-z]$',    # d m, k f (single letters with space)
    ]
    
    for pattern in obvious_patterns:
        if re.search(pattern, text):
            return True, f"Obvious spam pattern: {pattern}"
    
    return False, "Not obvious spam"

async def check_rapid_messaging(user_id: str, message_text: str) -> tuple[bool, str, dict]:
    """Smart rapid messaging detection"""
    now = time.time()
    
    # Get user's message times in the rapid window
    user_times = user_message_times[user_id]
    
    # Remove old messages outside the window
    user_times[:] = [t for t in user_times if now - t < RAPID_WINDOW_SECONDS]
    
    # Initialize stats
    stats = {
        "messages_in_window": len(user_times),
        "time_since_last": 0,
        "rapid_count": user_rapid_count.get(user_id, 0),
        "is_rapid": False,
        "is_flooding": False
    }
    
    # Check time since last message
    if user_id in user_last_message:
        time_diff = now - user_last_message[user_id]
        stats["time_since_last"] = time_diff
        
        # Check for rapid messaging
        if time_diff < RAPID_MESSAGE_THRESHOLD:
            user_rapid_count[user_id] += 1
            stats["rapid_count"] = user_rapid_count[user_id]
            stats["is_rapid"] = True
            
            # Too many rapid messages?
            if user_rapid_count[user_id] >= MAX_RAPID_MESSAGES:
                return True, f"Rapid messaging: {user_rapid_count[user_id]} fast messages", stats
        else:
            # Reset rapid count if enough time passed
            user_rapid_count[user_id] = 0
            stats["rapid_count"] = 0
    
    # Check for message flooding
    if len(user_times) >= MAX_MESSAGES_IN_WINDOW:
        stats["is_flooding"] = True
        return True, f"Message flooding: {len(user_times)} messages in {RAPID_WINDOW_SECONDS}s", stats
    
    # Update tracking
    user_last_message[user_id] = now
    user_times.append(now)
    
    return False, "Normal messaging rate", stats

async def handle_spam_intelligently(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   spam_type: str, reason: str, stats: dict = None):
    """Intelligent spam handling based on type and severity"""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name or "သုံးစွဲသူ"
    
    if DETAILED_SPAM_LOGGING:
        logger.info(f"Intelligent spam handling - User: {user_id}, Type: {spam_type}, Reason: {reason}")
        if stats:
            logger.info(f"Stats: {stats}")
    
    # Handle different spam types differently
    if spam_type == "rapid":
        # Rapid messaging - just ignore/delay, don't delete normal messages
        is_meaningful, _ = is_meaningful_message(update.message.text)
        
        if is_meaningful:
            # Meaningful message sent rapidly - just delay earning, keep message
            logger.info(f"Meaningful message sent rapidly by {user_id} - kept message, no earning")
            return "delayed"  # Special return code
        else:
            # Rapid spam - delete it
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
                logger.info(f"Deleted rapid spam from {user_id}")
            except:
                pass
            return "deleted"
    
    elif spam_type == "obvious":
        # Obvious spam - delete and warn
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
            
            # Send gentle warning
            user_warning_count[user_id] += 1
            warnings = user_warning_count[user_id]
            
            if warnings <= 3:  # Only warn first 3 times
                warning_messages = [
                    f"⚠️ {user_name} - အဓိပ္ပါယ်ရှိတဲ့စာများ ရေးပါ။ စပမ်မလုပ်ပါနှင့်!",
                    f"🚨 {user_name} - ကောင်းသောစာများ ရေးပြီး ငွေရှာပါ! ({warnings}/3)",
                    f"🔕 {user_name} - စပမ်မဲ့ အဓိပ္ပါယ်ပြည့်စုံတဲ့ စာများရေးပါ! ({warnings}/3)"
                ]
                
                warning_msg = warning_messages[min(warnings-1, 2)]
                
                try:
                    warning = await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=warning_msg
                    )
                    
                    # Auto-delete warning after 6 seconds
                    context.job_queue.run_once(
                        lambda context: delete_warning_message(context, update.effective_chat.id, warning.message_id),
                        6
                    )
                except:
                    pass
                    
            logger.info(f"Deleted obvious spam from {user_id}, warning {warnings}")
            
        except:
            pass
        return "deleted"
    
    elif spam_type == "flooding":
        # Message flooding - temporary ignore
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
            logger.info(f"Deleted flood message from {user_id}")
        except:
            pass
        return "deleted"
    
    return "ignored"

def delete_warning_message(context, chat_id, message_id):
    """Helper to delete warning message"""
    try:
        context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """INTELLIGENT message handler - maximum protection for normal users"""
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
        
        if LOG_NORMAL_USERS:
            logger.info(f"Processing message from {user_id}: {message_text[:50]}...")
        
        # INTELLIGENT SPAM ANALYSIS
        
        # Step 1: Check if message is meaningful (protect normal users)
        is_meaningful, meaningful_reason = is_meaningful_message(message_text)
        
        # Step 2: Check for rapid messaging
        is_rapid_spam, rapid_reason, rapid_stats = await check_rapid_messaging(user_id, message_text)
        
        # Step 3: Check for obvious spam
        is_obvious, obvious_reason = is_obvious_spam(message_text)
        
        # INTELLIGENT DECISION MATRIX
        
        process_earning = True
        action_taken = None
        
        if PROTECT_NORMAL_USERS and is_meaningful and not is_rapid_spam:
            # PRIORITY 1: NORMAL USER WITH MEANINGFUL MESSAGE
            if LOG_NORMAL_USERS:
                logger.info(f"Normal user {user_id}: meaningful message, allowing all - {meaningful_reason}")
            # Allow everything - message stays, earning processed
        
        elif is_meaningful and is_rapid_spam:
            # PRIORITY 2: NORMAL USER MESSAGING TOO FAST
            action_taken = await handle_spam_intelligently(update, context, "rapid", rapid_reason, rapid_stats)
            if action_taken == "delayed":
                # Message kept, but no earning for rapid messaging
                process_earning = False
                logger.info(f"Normal user {user_id} messaging rapidly: kept message, no earning")
            elif action_taken == "deleted":
                # Message deleted, no earning
                return
        
        elif not is_meaningful and is_rapid_spam:
            # PRIORITY 3: SPAM MESSAGE SENT RAPIDLY
            action_taken = await handle_spam_intelligently(update, context, "rapid", rapid_reason, rapid_stats)
            return  # Don't process earning
        
        elif not is_meaningful and is_obvious:
            # PRIORITY 4: OBVIOUS SPAM
            action_taken = await handle_spam_intelligently(update, context, "obvious", obvious_reason)
            return  # Don't process earning
        
        elif not is_meaningful and len(message_text.strip()) < 3:
            # PRIORITY 5: VERY SHORT NON-MEANINGFUL MESSAGE
            # Allow message but no earning
            process_earning = False
            logger.info(f"Very short message from {user_id}: allowing message, no earning")
        
        # If we reach here, message is allowed
        
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
        
        # Process earning if allowed
        if process_earning:
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
                    
                    if LOG_EARNING_NOTIFICATIONS:
                        logger.info(f"User {user_id} earned 1 {CURRENCY} in group {chat_id}")
                        
                except Exception as e:
                    logger.error(f"Failed to notify user {user_id} about earning: {e}")
    
    except Exception as e:
        logger.error(f"Error in intelligent message handler: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

def register_handlers(application: Application):
    """Register intelligent message handlers with maximum normal user protection"""
    logger.info("Registering INTELLIGENT message handlers with maximum normal user protection")
    
    # Handle all text messages in groups (not commands)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
        handle_message
    ))
    
    logger.info("✅ Intelligent message handlers registered successfully")
    
    # Log current configuration
    logger.info(f"🛡️ Normal user protection: {'ENABLED' if PROTECT_NORMAL_USERS else 'DISABLED'}")
    logger.info(f"🧠 Smart spam detection: {'ENABLED' if SMART_SPAM_DETECTION else 'DISABLED'}")
    logger.info(f"⚡ Rapid message threshold: {RAPID_MESSAGE_THRESHOLD} seconds")
    logger.info(f"🚨 Max rapid messages: {MAX_RAPID_MESSAGES}")
    logger.info(f"🪟 Rapid window: {RAPID_WINDOW_SECONDS} seconds")
    logger.info(f"📊 Max messages in window: {MAX_MESSAGES_IN_WINDOW}")
