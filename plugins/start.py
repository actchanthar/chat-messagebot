from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import logging
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from database.database import db
from config import CURRENCY, MESSAGE_RATE, MIN_WITHDRAWAL

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def advanced_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Advanced start command with interactive interface"""
    user_id = str(update.effective_user.id)
    user_name = {
        "first_name": update.effective_user.first_name or "",
        "last_name": update.effective_user.last_name or ""
    }
    
    # Check for referral
    referred_by = None
    if context.args and context.args[0].startswith("ref_"):
        referred_by = context.args[0][4:]
    
    user = await db.get_user(user_id)
    
    if not user:
        # Create new user
        user = await db.create_user(user_id, user_name, referred_by)
        
        # Award welcome bonus
        await db.add_bonus(user_id, 50)
        
        # Create welcome interface
        keyboard = [
            [
                InlineKeyboardButton("💰 Check Balance", callback_data="balance"),
                InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard")
            ],
            [
                InlineKeyboardButton("📊 My Stats", callback_data="user_stats"),
                InlineKeyboardButton("🎁 Referral Link", callback_data="referral_link")
            ],
            [
                InlineKeyboardButton("💸 How to Withdraw", callback_data="withdraw_info"),
                InlineKeyboardButton("ℹ️ Help & Guide", callback_data="help_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_message = f"""
🎉 **Welcome to the World's Most Advanced Earning Bot!**

🎁 **Welcome Bonus:** +50 {CURRENCY} added to your account!

💰 **How to Earn:**
• Chat in approved groups: {MESSAGE_RATE} messages = 1 {CURRENCY}
• Refer friends for bonuses
• Complete daily activities
• Participate in competitions

🌟 **Features:**
• Real-time earnings tracking
• Advanced leaderboards
• Secure withdrawal system
• Anti-spam protection
• Referral rewards

🚀 **Your Journey Starts Now!**
Choose an option below:
        """
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
        
        # Notify referrer
        if referred_by:
            try:
                await context.bot.send_message(
                    chat_id=referred_by,
                    text=f"🎉 {user_name.get('first_name', 'Someone')} joined using your referral link!\n💰 You earned 25 {CURRENCY} bonus!"
                )
            except:
                pass
    
    else:
        # Existing user dashboard
        current_balance = user.get('balance', 0)
        total_earnings = user.get('total_earnings', 0)
        messages_count = user.get('messages', 0)
        user_level = user.get('user_level', 1)
        
        keyboard = [
            [
                InlineKeyboardButton("💰 Balance", callback_data="balance"),
                InlineKeyboardButton("📊 Stats", callback_data="user_stats")
            ],
            [
                InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard"),
                InlineKeyboardButton("💸 Withdraw", callback_data="withdraw_info")
            ],
            [
                InlineKeyboardButton("🎁 Invite Friends", callback_data="referral_link"),
                InlineKeyboardButton("ℹ️ Help", callback_data="help_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        dashboard_message = f"""
👋 **Welcome back, {user_name.get('first_name', 'User')}!**

💰 **Balance:** {int(current_balance)} {CURRENCY}
📈 **Total Earned:** {int(total_earnings)} {CURRENCY}
📝 **Messages:** {messages_count:,}
🎯 **Level:** {user_level}

🚀 **Ready to earn more?**
        """
        
        await update.message.reply_text(dashboard_message, reply_markup=reply_markup)

async def handle_start_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle start menu callback queries"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    await query.answer()
    
    if data == "balance":
        # Show balance
        user = await db.get_user(user_id)
        if user:
            balance = user.get("balance", 0)
            await query.edit_message_text(
                f"💰 **Your Balance**\n\n"
                f"Current Balance: {int(balance)} {CURRENCY}\n"
                f"သင့်လက်ကျန်ငွေ: {int(balance)} ကျပ်\n\n"
                f"💡 Earn more by sending messages in approved groups!"
            )
    
    elif data == "user_stats":
        # Show user statistics
        user = await db.get_user(user_id)
        if user:
            stats_text = f"""
📊 **Your Statistics**

💰 Balance: {int(user.get('balance', 0))} {CURRENCY}
📝 Messages: {user.get('messages', 0):,}
🎯 Level: {user.get('user_level', 1)}
💸 Total Earned: {int(user.get('total_earnings', 0))} {CURRENCY}
👥 Referrals: {user.get('successful_referrals', 0)}

🚀 Keep chatting to level up!
            """
            await query.edit_message_text(stats_text)
    
    elif data == "show_leaderboard":
        # Show basic leaderboard
        try:
            top_users = await db.get_top_users(5, "total_earnings")
            leaderboard_text = "🏆 **TOP EARNERS**\n\n"
            
            for i, user in enumerate(top_users, 1):
                name = user.get('first_name', 'Unknown')[:15]
                earnings = user.get('total_earnings', 0)
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                leaderboard_text += f"{medal} {name} - {int(earnings)} {CURRENCY}\n"
            
            leaderboard_text += f"\n🎯 Use /top for full leaderboard!"
            await query.edit_message_text(leaderboard_text)
        except:
            await query.edit_message_text("📊 Leaderboard loading... Try /top command!")
    
    elif data == "referral_link":
        # Show referral link
        bot_username = context.bot.username or "YourBotUsername"
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        
        referral_text = f"""
👥 **Invite Friends & Earn!**

🔗 **Your Referral Link:**
`{referral_link}`

💰 **Earn 25 {CURRENCY} for each friend who:**
• Clicks your link and starts the bot
• Sends their first message

📊 Share this link and start earning!
        """
        await query.edit_message_text(referral_text)
    
    elif data == "withdraw_info":
        # Show withdrawal information
        withdraw_text = f"""
💸 **Withdrawal Information**

💰 **Minimum:** {MIN_WITHDRAWAL} {CURRENCY}
📱 **Methods:** KPay, WavePay, AYAPay, CBPay
⏱️ **Processing:** 24-48 hours

📋 **To request withdrawal:**
Use: `/withdraw <amount> <method> <phone>`

**Example:**
`/withdraw 1000 kpay 09123456789`

💡 Make sure you have enough balance!
        """
        await query.edit_message_text(withdraw_text)
    
    elif data == "help_menu":
        # Show help menu
        help_text = f"""
ℹ️ **Help & Commands**

💰 **Earning Commands:**
/balance - Check your balance
/stats - View your statistics
/withdraw - Request withdrawal

🏆 **Social Commands:**
/top - View leaderboards
/referral - Get your referral link

📋 **Other Commands:**
/help - Detailed help guide
/start - Return to main menu

💡 **How to Earn:**
1. Join approved groups
2. Send messages (3 messages = 1 kyat)
3. Invite friends for bonuses
4. Request withdrawal when ready!

🎯 **Support:** Contact admins for help
        """
        await query.edit_message_text(help_text)

def register_handlers(application: Application):
    """Register advanced start handlers"""
    # Replace the default start command with advanced version
    for handler in application.handlers[0][:]:
        if hasattr(handler, 'command') and 'start' in handler.command:
            application.handlers[0].remove(handler)
    
    application.add_handler(CommandHandler("start", advanced_start_command))
    application.add_handler(CallbackQueryHandler(handle_start_callbacks, pattern="^(balance|user_stats|show_leaderboard|referral_link|withdraw_info|help_menu)$"))
    
    logger.info("✅ Advanced start handlers registered")
