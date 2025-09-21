from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging
import sys
import os
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from database.database import db
from config import CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int) -> tuple[bool, list]:
    """Check if user is subscribed to required channels"""
    try:
        channels = await db.get_channels()
        if not channels:
            return True, []

        not_subscribed_channels = []
        for channel in channels:
            try:
                member = await context.bot.get_chat_member(channel["channel_id"], user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    not_subscribed_channels.append(channel)
            except Exception as e:
                logger.error(f"Error checking subscription: {e}")
                not_subscribed_channels.append(channel)

        return len(not_subscribed_channels) == 0, not_subscribed_channels
    except Exception as e:
        logger.error(f"Error in check_subscription: {e}")
        return True, []

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced start command with buttons - GUARANTEED TO SHOW BUTTONS"""
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"ENHANCED start command by user {user_id}")

    # Check for referral
    referred_by = None
    if context.args:
        try:
            ref_code = str(context.args[0])
            if ref_code.startswith("ref_"):
                referred_by = ref_code[4:]
            else:
                referred_by = ref_code
        except Exception as e:
            logger.error(f"Error parsing referral: {e}")

    # Check subscription
    subscribed, not_subscribed_channels = await check_subscription(context, int(user_id), chat_id)
    if not subscribed and not_subscribed_channels:
        keyboard = []
        for channel in not_subscribed_channels:
            channel_name = channel["channel_name"]
            if channel_name.startswith("@"):
                channel_name = channel_name[1:]
            
            keyboard.append([InlineKeyboardButton(
                f"📢 {channel['channel_name']}",
                url=f"https://t.me/{channel_name}"
            )])

        keyboard.append([InlineKeyboardButton("✅ I've Joined All", callback_data="check_subscription")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔐 **Subscription Required**\n\nPlease join all channels below:",
            reply_markup=reply_markup
        )
        return

    # Get or create user
    user = await db.get_user(user_id)
    is_new_user = False
    
    if not user:
        is_new_user = True
        user = await db.create_user(user_id, {
            "first_name": update.effective_user.first_name or "",
            "last_name": update.effective_user.last_name or ""
        }, referred_by)
        
        if not user:
            await update.message.reply_text("❌ Error creating account.")
            return

        # Award new user bonus
        welcome_bonus = 100
        await db.add_bonus(user_id, welcome_bonus)

    # Get user stats
    current_balance = user.get("balance", 0)
    total_messages = user.get("messages", 0) 
    user_level = user.get("user_level", 1)
    total_earnings = user.get("total_earnings", 0)
    successful_referrals = user.get("successful_referrals", 0)

    # Create welcome message
    if is_new_user:
        welcome_message = (
            f"စာပို့ရင်း ငွေရှာမယ်:\n"
            f"Welcome to the Chat Bot, {update.effective_user.first_name}! 🎉\n\n"
            f"🎁 Welcome Bonus: +100 {CURRENCY} added!\n\n"
            f"Earn money by sending messages in groups!\n"
            f"အုပ်စုတွင် စာပို့ခြင်းဖြင့် ငွေရှာပါ။\n\n"
        )
    else:
        welcome_message = (
            f"စာပို့ရင်း ငွေရှာမယ်:\n"
            f"Welcome back, {update.effective_user.first_name}! 🎉\n\n"
            f"💰 Balance: {int(current_balance)} {CURRENCY}\n"
            f"📝 Messages: {total_messages:,}\n"
            f"🎯 Level: {user_level}\n"
            f"💸 Total Earned: {int(total_earnings)} {CURRENCY}\n"
            f"👥 Referrals: {successful_referrals}\n\n"
        )

    # Add leaderboard (simplified for reliability)
    try:
        users = await db.get_all_users()
        if users and len(users) >= 3:
            sorted_users = sorted(users, key=lambda x: x.get("total_earnings", 0), reverse=True)[:10]
            
            if sorted_users and sorted_users[0].get("total_earnings", 0) > 0:
                phone_bill_reward = await db.get_phone_bill_reward()
                message_rate = await db.get_message_rate()
                
                top_message = (
                    f"🏆 Top Users (by earnings):\n\n"
                    f"(၇ ရက်တစ်ခါ Top 1-3 ရတဲ့လူကို {phone_bill_reward} မဲဖောက်ပေးပါတယ်):\n\n"
                )
                
                for i, top_user in enumerate(sorted_users[:5], 1):  # Show only top 5 for brevity
                    name = top_user.get('first_name', 'Unknown')
                    earnings = int(top_user.get('total_earnings', 0))
                    messages = top_user.get('messages', 0)
                    
                    if i <= 3:
                        top_message += f"{i}. <b>{name}</b> - {messages} msg, {earnings} {CURRENCY}\n"
                    else:
                        top_message += f"{i}. {name} - {messages} msg, {earnings} {CURRENCY}\n"
                
                welcome_message += top_message
    except Exception as e:
        logger.error(f"Error generating leaderboard: {e}")

    # Add instructions
    welcome_message += (
        f"\nCurrent earning rate: 3 messages = 1 {CURRENCY}\n"
        f"Use the buttons below to interact with the bot.\n"
        f"အောက်ပါခလုတ်များကို အသုံးပြုပါ။\n\n"
        f"Dev: @When_the_night_falls_my_soul_se\n"
        f"Updates Channel: https://t.me/ITAnimeAI"
    )

    # CREATE KEYBOARD WITH BUTTONS - THIS IS THE IMPORTANT PART
    keyboard = [
        [
            InlineKeyboardButton("Check Balance", callback_data="balance"),
            InlineKeyboardButton("Withdrawal", callback_data="withdraw")
        ],
        [
            InlineKeyboardButton("Dev", url="https://t.me/When_the_night_falls_my_soul_se"),
            InlineKeyboardButton("Updates Channel", url="https://t.me/ITAnimeAI")
        ],
        [
            InlineKeyboardButton("Join Earnings Group", url="https://t.me/stranger77777777777")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # SEND MESSAGE WITH BUTTONS
    try:
        await update.message.reply_text(
            welcome_message, 
            reply_markup=reply_markup, 
            parse_mode="HTML"
        )
        logger.info(f"BUTTONS sent to user {user_id}")
    except Exception as e:
        logger.error(f"HTML parse error: {e}")
        # Try without HTML parsing
        try:
            clean_message = welcome_message.replace("<b>", "").replace("</b>", "")
            await update.message.reply_text(clean_message, reply_markup=reply_markup)
            logger.info(f"BUTTONS sent (no HTML) to user {user_id}")
        except Exception as e2:
            logger.error(f"Failed to send with buttons: {e2}")
            # Last resort - send without buttons
            await update.message.reply_text(clean_message)

async def handle_start_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle start menu callbacks"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    await query.answer()
    
    if data == "balance":
        user = await db.get_user(user_id)
        if user:
            balance = user.get("balance", 0)
            await query.edit_message_text(
                f"💰 Your current balance is {int(balance)} {CURRENCY}.\n"
                f"သင့်လက်ကျန်ငွေသည် {int(balance)} ကျပ်ဖြစ်ပါသည်။"
            )
    
    elif data == "withdraw":
        await query.edit_message_text(
            "💸 **Withdrawal System**\n\n"
            "Use command: /withdraw\n"
            "Minimum: 200 kyat\n"
            "Processing: 24-48 hours"
        )

def register_handlers(application: Application):
    """Register start command handlers"""
    logger.info("Registering ENHANCED start handlers with BUTTONS")
    
    # Clear any existing start handlers first
    for handler_group in application.handlers.values():
        handlers_to_remove = []
        for handler in handler_group:
            if hasattr(handler, 'command') and 'start' in getattr(handler, 'command', []):
                handlers_to_remove.append(handler)
        for handler in handlers_to_remove:
            handler_group.remove(handler)
            logger.info("Removed existing start handler")
    
    # Add our start command
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(handle_start_callbacks))
    
    logger.info("✅ ENHANCED start handlers with BUTTONS registered successfully")
