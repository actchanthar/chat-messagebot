from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging
import sys
import os
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Updated start image URL
START_IMAGE_URL = "https://i.ibb.co/DDbgt0JC/x.jpg"

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced start command with image and custom design"""
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Start command by user {user_id} in chat {chat_id}")

    # Check for referral
    referred_by = None
    if context.args:
        try:
            ref_code = str(context.args[0])
            if ref_code.startswith("ref_"):
                referred_by = ref_code[4:]
            else:
                referred_by = ref_code
            logger.info(f"User {user_id} started with referral from {referred_by}")
        except Exception as e:
            logger.error(f"Error parsing referral ID for user {user_id}: {e}")

    # Check force subscription
    subscribed, not_subscribed_channels = await check_subscription(context, int(user_id), chat_id)
    if not subscribed:
        keyboard = []
        for i in range(0, len(not_subscribed_channels), 2):
            row = []
            channel_1 = not_subscribed_channels[i]
            row.append(InlineKeyboardButton(
                channel_1["channel_name"],
                url=f"https://t.me/{channel_1['channel_name'][1:]}"
            ))
            if i + 1 < len(not_subscribed_channels):
                channel_2 = not_subscribed_channels[i + 1]
                row.append(InlineKeyboardButton(
                    channel_2["channel_name"],
                    url=f"https://t.me/{channel_2['channel_name'][1:]}"
                ))
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Please join the following channels to use the bot:\n"
            "ကျေးဇူးပြု၍ အောက်ပါချန်နယ်များသို့ဝင်ရောက်ပါ။",
            reply_markup=reply_markup
        )
        logger.info(f"User {user_id} not subscribed to required channels: {[ch['channel_name'] for ch in not_subscribed_channels]}")
        return

    # Get or create user
    user = await db.get_user(user_id)
    is_new_user = False
    
    if not user:
        is_new_user = True
        user = await db.create_user(user_id, {
            "first_name": update.effective_user.first_name,
            "last_name": update.effective_user.last_name
        }, referred_by)
        if not user:
            logger.error(f"Failed to create user {user_id}")
            await update.message.reply_text("Error creating user. Please try again later.")
            return
        logger.info(f"Created new user {user_id} during start command")

        # Process referral bonus
        if referred_by:
            referrer = await db.get_user(referred_by)
            if referrer:
                referral_reward = await db.get_referral_reward()
                current_balance = referrer.get("balance", 0)
                new_invites = referrer.get("invites", 0) + 1
                successful_referrals = referrer.get("successful_referrals", 0) + 1
                
                await db.update_user(referred_by, {
                    "balance": current_balance + referral_reward,
                    "invites": new_invites,
                    "successful_referrals": successful_referrals
                })
                
                try:
                    await context.bot.send_message(
                        chat_id=referred_by,
                        text=f"🎉 **Your referral link worked!**\n\n"
                             f"👤 **{update.effective_user.first_name}** joined using your link!\n"
                             f"💰 **You earned:** {referral_reward} {CURRENCY}\n"
                             f"💵 **New Balance:** {int(current_balance + referral_reward)} {CURRENCY}\n"
                             f"🎯 **Keep sharing to earn more!**"
                    )
                    logger.info(f"Awarded {referral_reward} {CURRENCY} to referrer {referred_by} for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to notify referrer {referred_by}: {e}")

        # ANNOUNCE NEW USER
        try:
            from plugins.announcements import announcement_system
            await announcement_system.announce_new_user(
                user_id=user_id,
                user_name=update.effective_user.first_name or "New User",
                referred_by=referred_by,
                context=context
            )
        except Exception as e:
            logger.error(f"Failed to announce new user: {e}")

    # Get user stats
    current_balance = user.get("balance", 0)
    total_messages = user.get("messages", 0)
    user_level = user.get("user_level", 1)
    total_earnings = user.get("total_earnings", 0)
    successful_referrals = user.get("successful_referrals", 0)

    # Create welcome message with your custom format
    welcome_message = (
        f"စာပို့ရင်း ငွေရှာမယ်:\n"
        f"Welcome back, {update.effective_user.first_name}! 🎉\n\n"
        f"💰 Balance: {int(current_balance)} {CURRENCY}\n"
        f"📝 Messages: {total_messages}\n"
        f"🎯 Level: {user_level}\n"
        f"💸 Total Earned: {int(total_earnings)} {CURRENCY}\n"
        f"👥 Referrals: {successful_referrals}\n\n"
    )

    # Add top 5 users leaderboard as requested - FIXED
    try:
        users = await db.get_all_users()
        if users:
            # Sort by total earnings (as shown in your example)
            sorted_users = sorted(users, key=lambda x: x.get("total_earnings", 0), reverse=True)[:5]
            
            if sorted_users:
                for i, top_user in enumerate(sorted_users, 1):
                    # FIXED: Handle None values properly
                    name = top_user.get('first_name') or 'Unknown'
                    last_name = top_user.get('last_name') or ''
                    
                    # Only concatenate if last_name is not empty
                    if last_name:
                        full_name = f"{name} {last_name}".strip()
                    else:
                        full_name = name.strip()
                    
                    messages = top_user.get('messages', 0)
                    earnings = int(top_user.get('total_earnings', 0))
                    
                    welcome_message += f"{i}. {full_name} - {messages} msg, {earnings} {CURRENCY}\n"
                
    except Exception as e:
        logger.error(f"Error generating leaderboard: {e}")

    # Create custom keyboard with FIXED callback data to avoid conflicts
    keyboard = [
        [
            InlineKeyboardButton("Balance", callback_data="start_balance"),
            InlineKeyboardButton("Withdraw", callback_data="start_withdraw")
        ],
        [
            InlineKeyboardButton("ငွေထုတ်ချာနယ်", url="https://t.me/actearnproof"),
            InlineKeyboardButton("Join Group", url="https://t.me/+3Km76-24T3RjNzY1")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        # Send the image first
        await update.message.reply_photo(
            photo=START_IMAGE_URL,
            caption=welcome_message,
            reply_markup=reply_markup
        )
        logger.info(f"Sent welcome message with image to user {user_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send image, sending text only: {e}")
        # Fallback to text-only message if image fails
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def handle_start_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle start menu callbacks - FIXED to avoid withdrawal conflicts"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    await query.answer()
    logger.info(f"Processing start callback: {data} from user {user_id}")
    
    try:
        if data == "start_balance":
            user = await db.get_user(user_id)
            if user:
                balance = user.get("balance", 0)
                total_earned = user.get("total_earnings", 0)
                total_withdrawn = user.get("total_withdrawn", 0)
                messages = user.get("messages", 0)
                
                # Check for pending withdrawals
                pending_withdrawals = user.get("pending_withdrawals", [])
                pending_count = sum(1 for w in pending_withdrawals if w.get("status") == "PENDING")
                
                balance_text = (
                    f"💰 **Your Balance**\n\n"
                    f"💳 **Current Balance:** {int(balance)} {CURRENCY}\n"
                    f"📈 **Total Earned:** {int(total_earned)} {CURRENCY}\n"
                    f"💸 **Total Withdrawn:** {int(total_withdrawn)} {CURRENCY}\n"
                    f"📝 **Total Messages:** {messages:,}\n"
                    f"⏳ **Pending Withdrawals:** {pending_count}\n\n"
                    f"သင့်လက်ကျန်ငွေသည် {int(balance)} ကျပ်ဖြစ်ပါသည်။\n\n"
                    f"💡 Keep chatting in groups to earn more!\n"
                    f"📊 Rate: 3 messages = 1 {CURRENCY}\n"
                    f"📋 Use `/pending` to check withdrawal history"
                )
                
                # Send new message instead of editing photo
                await query.message.reply_text(balance_text)
            else:
                await query.message.reply_text("❌ User not found. Please try /start")
        
        elif data == "start_withdraw":
            # Guide user to use /withdraw command for secure processing
            user = await db.get_user(user_id)
            if user:
                balance = user.get("balance", 0)
                
                # Check for pending withdrawals
                pending_withdrawals = user.get("pending_withdrawals", [])
                pending_count = sum(1 for w in pending_withdrawals if w.get("status") == "PENDING")
                
                if pending_count > 0:
                    withdraw_text = (
                        f"⏳ **You have pending withdrawal requests**\n\n"
                        f"📊 **Current Status:**\n"
                        f"• Balance: {int(balance)} {CURRENCY}\n"
                        f"• Pending Requests: {pending_count}\n\n"
                        f"⏰ **Please wait for admin approval**\n"
                        f"📋 **Check status:** `/pending`\n\n"
                        f"သင့်တွင် ဆိုင်းငံ့ထားသော ငွေထုတ်မှု ရှိနေပါသည်။"
                    )
                else:
                    withdraw_text = (
                        f"💸 **Start Withdrawal Process**\n\n"
                        f"💰 **Your Balance:** {int(balance)} {CURRENCY}\n"
                        f"💎 **Minimum:** 200 {CURRENCY}\n\n"
                        f"🔐 **For secure withdrawal, use:**\n"
                        f"**`/withdraw`**\n\n"
                        f"✅ **Features:**\n"
                        f"• Secure payment method selection\n"
                        f"• Amount verification\n"
                        f"• Admin approval system\n"
                        f"• Balance protection\n\n"
                        f"📋 **Check history:** `/pending`\n\n"
                        f"ငွေထုတ်ရန် /withdraw ကိုအသုံးပြုပါ။"
                    )
                
                await query.message.reply_text(withdraw_text)
            else:
                await query.message.reply_text("❌ User not found. Please try /start first")
    
    except Exception as e:
        logger.error(f"Error processing start callback {data}: {e}")
        await query.message.reply_text(
            f"❌ Error occurred.\n\n"
            f"💡 **Try these commands:**\n"
            f"• `/withdraw` - Start withdrawal\n"
            f"• `/pending` - Check status\n"
            f"• `/start` - Restart bot"
        )

def register_handlers(application: Application):
    """Register start command handlers - FIXED callback patterns"""
    logger.info("Registering ENHANCED start handlers with IMAGE and CUSTOM DESIGN")
    application.add_handler(CommandHandler("start", start))
    
    # FIXED: Use specific patterns to avoid conflicts with withdrawal system
    application.add_handler(CallbackQueryHandler(
        handle_start_callbacks, 
        pattern="^start_(balance|withdraw)$"  # Only handle start_ prefixed callbacks
    ))
    
    logger.info("✅ ENHANCED start handlers with IMAGE and CUSTOM DESIGN registered successfully")
