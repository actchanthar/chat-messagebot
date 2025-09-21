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
from config import CURRENCY, ADMIN_IDS

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
        return True, []  # Allow access on error

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ADVANCED START COMMAND - Will show buttons"""
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"ADVANCED start command by user {user_id}")

    # Check for referral
    referred_by = None
    if context.args:
        try:
            ref_code = str(context.args[0])
            if ref_code.startswith("ref_"):
                referred_by = ref_code[4:]
            else:
                referred_by = ref_code
            logger.info(f"User {user_id} referred by {referred_by}")
        except Exception as e:
            logger.error(f"Error parsing referral: {e}")

    # Check subscription (if channels exist)
    subscribed, not_subscribed_channels = await check_subscription(context, int(user_id), chat_id)
    if not subscribed and not_subscribed_channels:
        keyboard = []
        for i in range(0, len(not_subscribed_channels), 2):
            row = []
            channel_1 = not_subscribed_channels[i]
            channel_name = channel_1["channel_name"]
            if channel_name.startswith("@"):
                channel_name = channel_name[1:]
            
            row.append(InlineKeyboardButton(
                f"📢 {channel_1['channel_name']}",
                url=f"https://t.me/{channel_name}"
            ))
            
            if i + 1 < len(not_subscribed_channels):
                channel_2 = not_subscribed_channels[i + 1]
                channel_name_2 = channel_2["channel_name"]
                if channel_name_2.startswith("@"):
                    channel_name_2 = channel_name_2[1:]
                row.append(InlineKeyboardButton(
                    f"📢 {channel_2['channel_name']}",
                    url=f"https://t.me/{channel_name_2}"
                ))
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("✅ I've Joined All Channels", callback_data="check_subscription")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔐 **Subscription Required**\n\n"
            "Please join ALL channels below:\n"
            "ကျေးဇူးပြု၍ အောက်ပါချန်နယ်များသို့ဝင်ရောက်ပါ။",
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
            await update.message.reply_text("❌ Error creating account. Please try again.")
            return

        # Award new user bonus
        welcome_bonus = 100
        await db.add_bonus(user_id, welcome_bonus)
        logger.info(f"New user {user_id} created with {welcome_bonus} {CURRENCY} bonus")

    # Get user stats for dashboard
    current_balance = user.get("balance", 0)
    total_messages = user.get("messages", 0) 
    user_level = user.get("user_level", 1)
    total_earnings = user.get("total_earnings", 0)
    successful_referrals = user.get("successful_referrals", 0)

    # Create welcome message with stats
    if is_new_user:
        welcome_message = (
            f"စာပို့ရင်း ငွေရှာမယ်:\n"
            f"Welcome to the Chat Bot, {update.effective_user.first_name}! 🎉\n\n"
            f"🎁 Welcome Bonus: +100 {CURRENCY} added!\n\n"
            f"Earn money by sending messages in the group!\n"
            f"အုပ်စုတွင် စာပို့ခြင်းဖြင့် ငွေရှာပါ။\n\n"
            f"Invite friends using your referral link!\n"
            f"Each invite earns you 25 {CURRENCY}!\n\n"
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

    # Add leaderboard section
    try:
        users = await db.get_all_users()
        if users and len(users) >= 3:
            top_users = await db.get_top_users(10, "total_earnings")
            
            if top_users and len(top_users) > 0:
                phone_bill_reward = await db.get_phone_bill_reward()
                message_rate = await db.get_message_rate()
                
                top_message = (
                    f"🏆 Top Users (by earnings):\n\n"
                    f"(၇ ရက်တစ်ခါ Top 1-3 ရတဲ့လူကို {phone_bill_reward} မဲဖောက်ပေးပါတယ်):\n\n"
                )
                
                for i, top_user in enumerate(top_users[:10], 1):
                    name = top_user.get('first_name', 'Unknown')
                    last_name = top_user.get('last_name', '')
                    full_name = (name + ' ' + last_name).strip()
                    
                    earnings = top_user.get('total_earnings', 0)
                    messages = top_user.get('messages', 0)
                    
                    if i <= 3:
                        top_message += f"{i}. <b>{full_name}</b> - {messages} msg, {int(earnings)} {CURRENCY}\n"
                    else:
                        top_message += f"{i}. {full_name} - {messages} msg, {int(earnings)} {CURRENCY}\n"
                
                welcome_message += top_message
    except Exception as e:
        logger.error(f"Error generating leaderboard: {e}")

    # Add current earning rate info
    try:
        message_rate = await db.get_message_rate()
        welcome_message += (
            f"\nCurrent earning rate: {message_rate} messages = 1 {CURRENCY}\n"
            f"Use the buttons below to interact with the bot.\n"
            f"အောက်ပါခလုတ်များကို အသုံးပြုပါ။"
        )
    except:
        welcome_message += (
            f"\nCurrent earning rate: 3 messages = 1 {CURRENCY}\n"
            f"Use the buttons below to interact with the bot.\n"
            f"အောက်ပါခလုတ်များကို အသုံးပြုပါ။"
        )

    # IMPORTANT: Create the keyboard with buttons
    keyboard = [
        [
            InlineKeyboardButton("Check Balance", callback_data="balance"),
            InlineKeyboardButton("Withdrawal", callback_data="withdraw")
        ],
        [
            InlineKeyboardButton("📊 My Stats", callback_data="detailed_stats"),
            InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard")
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

    try:
        # Send message with buttons
        await update.message.reply_text(
            welcome_message, 
            reply_markup=reply_markup, 
            parse_mode="HTML"
        )
        logger.info(f"Advanced welcome with buttons sent to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send welcome message: {e}")
        # Fallback without HTML parsing
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def handle_start_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle start menu callback queries"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    await query.answer()
    
    try:
        if data == "check_subscription":
            subscribed, not_subscribed = await check_subscription(context, int(user_id), query.message.chat_id)
            if subscribed:
                await query.edit_message_text("✅ **Subscription Verified!**\n\nWelcome! Use /start to begin.")
            else:
                await query.answer("❌ Please join ALL channels first!", show_alert=True)
        
        elif data == "balance":
            user = await db.get_user(user_id)
            if user:
                balance = user.get("balance", 0)
                total_earned = user.get("total_earnings", 0)
                await query.edit_message_text(
                    f"💰 Your current balance is {int(balance)} {CURRENCY}.\n"
                    f"သင့်လက်ကျန်ငွေသည် {int(balance)} ကျပ်ဖြစ်ပါသည်။\n\n"
                    f"📈 Total Earned: {int(total_earned)} {CURRENCY}\n\n"
                    f"💡 Keep chatting in groups to earn more!"
                )
        
        elif data == "withdraw":
            # Start withdrawal process
            try:
                from plugins.withdrawal import withdraw
                context.user_data.clear()
                # Call withdraw function directly
                await withdraw(update, context)
            except Exception as e:
                logger.error(f"Error starting withdrawal: {e}")
                await query.edit_message_text(
                    "💸 **Withdrawal System**\n\n"
                    "Use the command: `/withdraw`\n"
                    "Available methods: KBZ Pay, Wave Pay, AYA Pay, CB Pay\n\n"
                    "Minimum: 200 kyat\n"
                    "Processing: 24-48 hours"
                )
        
        elif data == "detailed_stats":
            user = await db.get_user(user_id)
            if user:
                try:
                    rank = await db.get_user_rank_by_earnings(user_id)
                    messages_today = await db.get_user_messages_today(user_id)
                except:
                    rank = 0
                    messages_today = 0
                
                stats_text = f"""
📊 **YOUR STATISTICS**

👤 **Profile:**
• Name: {user.get('first_name', 'Unknown')} {user.get('last_name', '')}
• Level: {user.get('user_level', 1)}
• Rank: #{rank if rank > 0 else 'N/A'}

💰 **Financial:**
• Balance: {int(user.get('balance', 0))} {CURRENCY}
• Total Earned: {int(user.get('total_earnings', 0))} {CURRENCY}
• Total Withdrawn: {int(user.get('total_withdrawn', 0))} {CURRENCY}

📝 **Activity:**
• Total Messages: {user.get('messages', 0):,}
• Messages Today: {messages_today}
• Last Active: {user.get('last_activity', datetime.utcnow()).strftime('%Y-%m-%d')}

👥 **Referrals:**
• Successful Referrals: {user.get('successful_referrals', 0)}
• Total Invites: {user.get('invites', 0)}
                """
                await query.edit_message_text(stats_text)
        
        elif data == "show_leaderboard":
            try:
                top_users = await db.get_top_users(10, "total_earnings")
                if not top_users:
                    await query.edit_message_text("🏆 **Leaderboard**\n\nNo users found yet! Start earning to be first!")
                    return
                
                leaderboard_text = "🏆 **TOP EARNERS LEADERBOARD**\n\n"
                
                for i, user in enumerate(top_users[:10], 1):
                    name = user.get('first_name', 'Unknown')[:15]
                    earnings = user.get('total_earnings', 0)
                    level = user.get('user_level', 1)
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    leaderboard_text += f"{medal} {name} - {int(earnings)} {CURRENCY} | Lv.{level}\n"
                
                leaderboard_text += "\n🎯 Keep earning to climb higher!"
                await query.edit_message_text(leaderboard_text)
            except Exception as e:
                logger.error(f"Error showing leaderboard: {e}")
                await query.edit_message_text("🏆 **Leaderboard**\n\nUse /top command for rankings!")
    
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        await query.edit_message_text("❌ Error occurred. Please try /start again.")

def register_handlers(application: Application):
    """Register start command handlers"""
    logger.info("Registering ADVANCED start command handlers")
    
    # Clear any existing start handlers
    for handler_group in application.handlers.values():
        for handler in handler_group[:]:
            if hasattr(handler, 'command') and 'start' in getattr(handler, 'command', []):
                handler_group.remove(handler)
                logger.info("Removed existing start handler")
    
    # Register our advanced start command
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(handle_start_callbacks))
    
    logger.info("✅ ADVANCED start handlers registered successfully")
