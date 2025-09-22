from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from telegram.error import TelegramError
import logging
import sys
import os
from collections import defaultdict
import time
import re
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import APPROVED_GROUPS, CURRENCY, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Anti-spam tracking
user_message_history = defaultdict(list)
user_spam_warnings = defaultdict(int)
user_temp_bans = {}

# Spam detection parameters
RAPID_MESSAGE_THRESHOLD = 3  # Messages in time window
RAPID_TIME_WINDOW = 10       # Seconds
FLOOD_MESSAGE_THRESHOLD = 8  # Messages in larger window
FLOOD_TIME_WINDOW = 30       # Seconds
MAX_IDENTICAL_MESSAGES = 3   # Same message repetitions
SPAM_WARNING_THRESHOLD = 3   # Warnings before temp ban
TEMP_BAN_DURATION = 300      # 5 minutes

def is_meaningful_message(text: str) -> bool:
    """Check if message has meaningful content"""
    if not text or len(text.strip()) < 2:
        return False
    
    # Remove emojis and special characters for analysis
    clean_text = re.sub(r'[^\w\s]', '', text.lower().strip())
    
    if len(clean_text) < 2:
        return False
    
    # Common spam patterns
    spam_patterns = [
        r'^(.)\1{4,}$',  # Repeated characters like 'aaaaa'
        r'^(..)\1{3,}$', # Repeated pairs like 'hahaha'
        r'^\d+$',        # Only numbers
        r'^[!@#$%^&*()]+$', # Only special characters
    ]
    
    for pattern in spam_patterns:
        if re.match(pattern, clean_text):
            return False
    
    # Check for repeated words
    words = clean_text.split()
    if len(words) > 1:
        unique_words = set(words)
        if len(unique_words) == 1 and len(words) > 3:  # Same word repeated
            return False
    
    return True

async def analyze_spam_behavior(user_id: str, message_text: str, chat_id: int) -> dict:
    """Analyze user's messaging behavior for spam detection"""
    current_time = time.time()
    
    # Clean old message history (older than flood window)
    user_message_history[user_id] = [
        msg for msg in user_message_history[user_id] 
        if current_time - msg['time'] < FLOOD_TIME_WINDOW
    ]
    
    # Add current message
    user_message_history[user_id].append({
        'text': message_text,
        'time': current_time,
        'chat_id': chat_id
    })
    
    messages = user_message_history[user_id]
    
    # Analyze recent messages
    recent_messages = [msg for msg in messages if current_time - msg['time'] < RAPID_TIME_WINDOW]
    rapid_count = len(recent_messages)
    
    # Check for flooding
    flood_count = len(messages)
    
    # Check for identical messages
    recent_texts = [msg['text'] for msg in recent_messages[-5:]]
    identical_count = max([recent_texts.count(text) for text in set(recent_texts)]) if recent_texts else 0
    
    # Calculate time since last message
    time_since_last = 0
    if len(messages) >= 2:
        time_since_last = messages[-1]['time'] - messages[-2]['time']
    
    # Determine spam type
    is_rapid = rapid_count >= RAPID_MESSAGE_THRESHOLD
    is_flooding = flood_count >= FLOOD_MESSAGE_THRESHOLD
    is_identical = identical_count >= MAX_IDENTICAL_MESSAGES
    
    return {
        'messages_in_window': len(recent_messages),
        'time_since_last': time_since_last,
        'rapid_count': rapid_count,
        'flood_count': flood_count,
        'identical_count': identical_count,
        'is_rapid': is_rapid,
        'is_flooding': is_flooding,
        'is_identical': is_identical,
        'is_spam': is_rapid or is_flooding or is_identical
    }

async def handle_spam_detection(user_id: str, user_name: str, spam_analysis: dict, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Handle spam detection and apply appropriate actions"""
    
    # Determine spam severity
    spam_reasons = []
    if spam_analysis['is_rapid']:
        spam_reasons.append(f"Rapid messaging: {spam_analysis['rapid_count']} fast messages")
    if spam_analysis['is_flooding']:
        spam_reasons.append(f"Flooding: {spam_analysis['flood_count']} messages in {FLOOD_TIME_WINDOW}s")
    if spam_analysis['is_identical']:
        spam_reasons.append(f"Identical messages: {spam_analysis['identical_count']} repeats")
    
    if not spam_reasons:
        return False
    
    spam_type = "rapid" if spam_analysis['is_rapid'] else "flood" if spam_analysis['is_flooding'] else "identical"
    reason = "; ".join(spam_reasons)
    
    logger.info(f"Intelligent spam handling - User: {user_id}, Type: {spam_type}, Reason: {reason}")
    logger.info(f"Stats: {spam_analysis}")
    
    # Check if user is admin
    if user_id in ADMIN_IDS:
        logger.info(f"Admin {user_id} detected as spam but not penalized")
        return False
    
    # Increment spam warnings
    user_spam_warnings[user_id] += 1
    current_warnings = user_spam_warnings[user_id]
    
    # Apply progressive penalties
    if current_warnings >= SPAM_WARNING_THRESHOLD:
        # Temporary ban
        ban_until = time.time() + TEMP_BAN_DURATION
        user_temp_bans[user_id] = ban_until
        
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"⚠️ **{user_name}** has been temporarily restricted for spam.\n"
                    f"🕐 **Duration:** {TEMP_BAN_DURATION//60} minutes\n"
                    f"📝 **Reason:** {reason}\n"
                    f"💡 **Please chat normally to avoid restrictions.**"
                )
            )
        except Exception as e:
            logger.error(f"Failed to send spam notification: {e}")
        
        logger.warning(f"User {user_id} temporarily banned for {TEMP_BAN_DURATION//60} minutes - {reason}")
        return True
    
    else:
        # Warning message
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"⚠️ **Spam Warning {current_warnings}/{SPAM_WARNING_THRESHOLD}** for {user_name}\n"
                    f"📝 **Reason:** {reason}\n"
                    f"💡 **Please slow down and chat normally.**"
                )
            )
        except Exception as e:
            logger.error(f"Failed to send warning: {e}")
        
        logger.warning(f"Spam warning {current_warnings} for user {user_id} - {reason}")
        return False

def is_user_temp_banned(user_id: str) -> bool:
    """Check if user is temporarily banned"""
    if user_id not in user_temp_bans:
        return False
    
    if time.time() > user_temp_bans[user_id]:
        # Ban expired
        del user_temp_bans[user_id]
        user_spam_warnings[user_id] = max(0, user_spam_warnings[user_id] - 1)  # Reduce warnings
        return False
    
    return True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all messages and process earnings with milestone notifications"""
    try:
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
        spam_analysis = await analyze_spam_behavior(user_id, message_text, chat_id)
        
        # Handle spam detection
        if spam_analysis['is_spam']:
            spam_handled = await handle_spam_detection(user_id, user_name, spam_analysis, context, chat_id)
            
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
    """Register message handlers with anti-spam system"""
    logger.info("Registering message handlers with intelligent anti-spam system")
    
    # Handle all text messages in groups
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND,
        handle_message
    ))
    
    logger.info("✅ Message handlers with milestone notifications registered successfully")
