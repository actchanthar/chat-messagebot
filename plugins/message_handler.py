from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import logging
import time
import re
from collections import defaultdict, deque
from datetime import datetime, timezone
import asyncio
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import APPROVED_GROUPS, CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Anti-spam system - In-memory storage
user_message_history = defaultdict(lambda: deque(maxlen=10))  # Store last 10 message times
user_content_history = defaultdict(lambda: deque(maxlen=5))   # Store last 5 message contents
user_warnings = defaultdict(int)  # Warning count per user
temp_banned_users = set()  # Temporarily banned users
user_temp_ban_until = {}  # Ban expiry times

# Spam detection parameters
RAPID_MESSAGE_THRESHOLD = 3  # messages
RAPID_MESSAGE_WINDOW = 10    # seconds
DUPLICATE_THRESHOLD = 3      # repeated messages
WARNING_THRESHOLD = 2        # warnings before temp ban
TEMP_BAN_DURATION = 300      # 5 minutes

def is_meaningful_message(text: str) -> bool:
    """Check if message contains meaningful content"""
    if not text or len(text.strip()) < 3:
        return False
    
    # Check for common spam patterns
    spam_patterns = [
        r'^(.)\1{4,}$',  # Repeated characters (aaaaa)
        r'^[!@#$%^&*()_+-=\[\]{}|;:,.<>?/~`]{4,}$',  # Only symbols
        r'^[0-9\s]+$',   # Only numbers and spaces
        r'^[a-zA-Z]\s[a-zA-Z]\s[a-zA-Z]',  # Single letters spaced out
        r'^\s*$',        # Only whitespace
    ]
    
    for pattern in spam_patterns:
        if re.match(pattern, text.strip()):
            return False
    
    # Check for meaningful words (at least 2 characters)
    words = text.strip().split()
    meaningful_words = [w for w in words if len(w) >= 2 and not w.isdigit()]
    
    return len(meaningful_words) >= 1

def is_user_temp_banned(user_id: str) -> bool:
    """Check if user is temporarily banned"""
    if user_id in temp_banned_users:
        # Check if ban expired
        if user_id in user_temp_ban_until:
            if time.time() > user_temp_ban_until[user_id]:
                # Ban expired, remove user
                temp_banned_users.discard(user_id)
                del user_temp_ban_until[user_id]
                logger.info(f"Temp ban expired for user {user_id}")
                return False
        return True
    return False

async def analyze_spam_behavior(user_id: str, message_text: str, chat_id: str) -> dict:
    """Analyze user's messaging behavior for spam detection"""
    current_time = time.time()
    
    # Add current message time to history
    user_message_history[user_id].append(current_time)
    user_content_history[user_id].append(message_text.lower().strip())
    
    # Check for rapid messaging
    recent_messages = list(user_message_history[user_id])
    if len(recent_messages) >= RAPID_MESSAGE_THRESHOLD:
        time_diff = recent_messages[-1] - recent_messages[-RAPID_MESSAGE_THRESHOLD]
        is_rapid = time_diff < RAPID_MESSAGE_WINDOW
    else:
        is_rapid = False
    
    # Check for duplicate content
    recent_content = list(user_content_history[user_id])
    duplicate_count = recent_content.count(message_text.lower().strip())
    is_duplicate = duplicate_count >= DUPLICATE_THRESHOLD
    
    # Check for meaningless content
    is_meaningless = not is_meaningful_message(message_text)
    
    # Determine overall spam score
    spam_score = 0
    if is_rapid:
        spam_score += 1
    if is_duplicate:
        spam_score += 2
    if is_meaningless:
        spam_score += 1
    
    return {
        'is_spam': spam_score >= 2,
        'is_rapid': is_rapid,
        'is_duplicate': is_duplicate,
        'is_meaningless': is_meaningless,
        'spam_score': spam_score,
        'duplicate_count': duplicate_count
    }

async def handle_spam_detection(user_id: str, user_name: str, spam_analysis: dict, context: ContextTypes.DEFAULT_TYPE, chat_id: str) -> bool:
    """Handle spam detection and apply appropriate actions"""
    
    if spam_analysis['spam_score'] >= 3 or spam_analysis['duplicate_count'] >= 3:
        # Severe spam - immediate temp ban
        user_warnings[user_id] = WARNING_THRESHOLD
        temp_banned_users.add(user_id)
        user_temp_ban_until[user_id] = time.time() + TEMP_BAN_DURATION
        
        logger.warning(f"User {user_id} temp banned for severe spam (score: {spam_analysis['spam_score']})")
        
        # Notify user privately
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"⚠️ **TEMPORARY BAN - 5 MINUTES**\n\n"
                    f"🚫 **Reason:** Spam/Duplicate messages detected\n\n"
                    f"📋 **What happened:**\n"
                    f"• {'Rapid messaging, ' if spam_analysis['is_rapid'] else ''}"
                    f"{'Duplicate content, ' if spam_analysis['is_duplicate'] else ''}"
                    f"{'Meaningless messages' if spam_analysis['is_meaningless'] else ''}\n\n"
                    f"⏰ **Ban expires in:** 5 minutes\n"
                    f"💡 **After ban:** Send meaningful, unique messages\n\n"
                    f"🔄 **Future violations may result in longer bans**"
                )
            )
        except Exception as e:
            logger.error(f"Failed to notify temp banned user {user_id}: {e}")
        
        return True
    
    elif spam_analysis['is_spam']:
        # Moderate spam - increase warning
        user_warnings[user_id] += 1
        
        if user_warnings[user_id] >= WARNING_THRESHOLD:
            # Temp ban after warnings
            temp_banned_users.add(user_id)
            user_temp_ban_until[user_id] = time.time() + TEMP_BAN_DURATION
            
            logger.warning(f"User {user_id} temp banned after {user_warnings[user_id]} warnings")
            
            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🚫 **TEMPORARY BAN - 5 MINUTES**\n\n"
                        f"⚠️ **Reason:** Multiple spam warnings\n\n"
                        f"📊 **Your spam score:** {spam_analysis['spam_score']}/5\n"
                        f"⚠️ **Warnings received:** {user_warnings[user_id]}\n\n"
                        f"⏰ **Ban expires:** 5 minutes\n"
                        f"💡 **Send quality messages to avoid future bans**"
                    )
                )
            except Exception as e:
                logger.error(f"Failed to notify warned user {user_id}: {e}")
            
            return True
        else:
            # Just a warning
            logger.info(f"User {user_id} received spam warning {user_warnings[user_id]}/{WARNING_THRESHOLD}")
            
            # Send private warning (don't notify in group)
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"⚠️ **SPAM WARNING {user_warnings[user_id]}/{WARNING_THRESHOLD}**\n\n"
                        f"📊 **Detected issues:**\n"
                        f"{'• Rapid messaging\n' if spam_analysis['is_rapid'] else ''}"
                        f"{'• Duplicate messages\n' if spam_analysis['is_duplicate'] else ''}"
                        f"{'• Low-quality content\n' if spam_analysis['is_meaningless'] else ''}"
                        f"\n💡 **Please send meaningful, unique messages**\n"
                        f"🚫 **Next warning = 5 minute ban**"
                    )
                )
            except Exception as e:
                logger.error(f"Failed to send warning to user {user_id}: {e}")
    
    return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all messages and process earnings with milestone notifications - FIXED"""
    try:
        # Check if this is a callback query or channel post - SKIP THESE
        if update.callback_query or update.channel_post or update.edited_message or update.edited_channel_post:
            return
        
        # Check if update.message exists
        if not update.message:
            logger.warning("Received update without message object")
            return
        
        # Check if message has text
        if not hasattr(update.message, 'text') or update.message.text is None:
            logger.info("Received non-text message, skipping earning processing")
            return
        
        user_id = str(update.effective_user.id)
        chat_id = update.effective_chat.id
        message_text = update.message.text or ""
        
        # Skip if not in approved groups
        if str(chat_id) not in APPROVED_GROUPS:
            return
        
        # Check if user is temporarily banned
        if is_user_temp_banned(user_id):
            try:
                await update.message.delete()
                logger.info(f"Deleted message from temp-banned user {user_id}")
            except Exception as e:
                logger.error(f"Failed to delete message from banned user: {e}")
            return
        
        # Get user from database
        user = await db.get_user(user_id)
        if not user:
            # Create user if doesn't exist
            user_data = {
                "first_name": update.effective_user.first_name or "",
                "last_name": update.effective_user.last_name or "",
                "username": update.effective_user.username or ""
            }
            user = await db.create_user(user_id, user_data)
            if not user:
                return
        
        # Check if user is banned
        if user.get("banned", False):
            return
        
        # Get user name for notifications
        user_name = user.get("first_name", "User")
        
        # Check meaningful content
        is_meaningful = is_meaningful_message(message_text)
        
        # Analyze spam behavior
        spam_analysis = await analyze_spam_behavior(user_id, message_text, str(chat_id))
        
        # Handle spam detection
        if spam_analysis['is_spam']:
            spam_handled = await handle_spam_detection(user_id, user_name, spam_analysis, context, str(chat_id))
            
            if spam_handled:
                # User was temp banned
                try:
                    await update.message.delete()
                except:
                    pass
                return
            
            # User got warning but message kept
            if is_meaningful:
                logger.info(f"Meaningful message sent rapidly by {user_id} - kept message, no earning")
            else:
                logger.info(f"Spam message from {user_id} - kept message, no earning, no processing")
                return
            
            # For rapid messaging, keep message but don't give earning
            if spam_analysis['is_rapid']:
                logger.info(f"Normal user {user_id} messaging rapidly: kept message, no earning")
                return
        
        # Check referral rewards (do this for every message to catch channel joins/leaves)
        try:
            await db.check_and_process_referral_reward(user_id, context)
        except Exception as e:
            logger.error(f"Error checking referral rewards for {user_id}: {e}")
        
        # Process message and earning
        earned = await db.process_message_earning(user_id, str(chat_id), context)
        
        if earned:
            # Get updated user data to check milestones
            updated_user = await db.get_user(user_id)
            current_balance = updated_user.get("balance", 0)
            
            # Check for milestone achievements - ONLY MAJOR MILESTONES
            milestone_reached = None
            if current_balance >= 100000 and (current_balance - 1) < 100000:
                milestone_reached = "100K"
            elif current_balance >= 50000 and (current_balance - 1) < 50000:
                milestone_reached = "50K"
            elif current_balance >= 25000 and (current_balance - 1) < 25000:
                milestone_reached = "25K"
            elif current_balance >= 10000 and (current_balance - 1) < 10000:
                milestone_reached = "10K"
            elif current_balance >= 5000 and (current_balance - 1) < 5000:
                milestone_reached = "5K"
            elif current_balance >= 1000 and (current_balance - 1) < 1000:
                milestone_reached = "1K"
            
            # Only send notification for major milestones
            should_notify = False
            if milestone_reached:
                should_notify = True
            elif current_balance % 10000 == 0 and current_balance >= 10000:  # Every 10K after first 10K
                should_notify = True
                milestone_reached = f"{current_balance//1000}K"
            
            if should_notify:
                if milestone_reached in ["100K", "50K"]:
                    # MEGA milestone message
                    milestone_msg = (
                        f"🎊🎉 **MEGA MILESTONE ACHIEVED!** 🎉🎊\n\n"
                        f"👑 **{user_name}** just reached **{milestone_reached} {CURRENCY}!** 👑\n\n"
                        f"💰 **Current Balance:** {current_balance:,} {CURRENCY}\n"
                        f"📈 **Total Earned:** {updated_user.get('total_earnings', 0):,} {CURRENCY}\n"
                        f"💬 **Messages:** {updated_user.get('messages', 0):,}\n\n"
                        f"🔥🔥 **INCREDIBLE ACHIEVEMENT!** 🔥🔥\n"
                        f"🏆 **You're among the top earners!**"
                    )
                elif milestone_reached in ["25K", "10K", "5K"]:
                    # Major milestone message
                    milestone_msg = (
                        f"🎉 **MAJOR MILESTONE!** 🎉\n\n"
                        f"⭐ **{user_name}** reached **{milestone_reached} {CURRENCY}!** ⭐\n\n"
                        f"💰 **Balance:** {current_balance:,} {CURRENCY}\n"
                        f"💬 **Messages:** {updated_user.get('messages', 0):,}\n\n"
                        f"🚀 **Keep going for even bigger milestones!**"
                    )
                elif milestone_reached == "1K":
                    # First 1K milestone
                    milestone_msg = (
                        f"🎊 **FIRST 1K MILESTONE!** 🎊\n\n"
                        f"🎯 **{user_name}** reached **1,000 {CURRENCY}!**\n\n"
                        f"💪 **Great start! Keep chatting to earn more!**\n"
                        f"🎁 **Next milestone: 5,000 {CURRENCY}**"
                    )
                else:
                    # Regular milestone (10K intervals)
                    milestone_msg = (
                        f"💰 **{user_name}** reached **{milestone_reached} {CURRENCY}!**\n"
                        f"🔥 **Amazing progress! Keep earning!**"
                    )
                
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=milestone_msg,
                        reply_to_message_id=update.message.message_id
                    )
                    logger.info(f"User {user_id} milestone notification sent: {milestone_reached} - {current_balance} {CURRENCY}")
                except Exception as e:
                    logger.error(f"Failed to send milestone notification: {e}")
            
            # Log earning without notification for regular earnings
            logger.info(f"User {user_id} earned 1 {CURRENCY} in group {chat_id}")
        
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

def register_handlers(application: Application):
    """Register message handlers with anti-spam system - FIXED FILTER"""
    logger.info("Registering message handlers with intelligent anti-spam system")
    
    # Handle all TEXT messages in GROUPS only - EXCLUDE commands
    # Callback queries are automatically excluded because they don't have text messages
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND,
        handle_message
    ))
    
    logger.info("✅ Message handlers with milestone notifications registered successfully")
    logger.info("✅ Anti-spam system active with intelligent detection")
    logger.info("✅ Only text messages in groups will be processed for earnings")
