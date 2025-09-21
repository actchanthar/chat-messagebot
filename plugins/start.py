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
from utils.achievement_system import achievement_system
from utils.economy_manager import economy_manager

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Advanced start command with welcome interface"""
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
        # Create new user with advanced features
        user = await db.create_user(user_id, user_name, referred_by)
        
        # Award first-time bonus
        await db.add_bonus(user_id, 50)  # 50 kyat welcome bonus
        
        # Check for achievements
        await achievement_system.check_achievements(user_id, "first_start")
        
        # Create welcome interface
        keyboard = [
            [
                InlineKeyboardButton("💰 Check Balance", callback_data="balance"),
                InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")
            ],
            [
                InlineKeyboardButton("🎯 Daily Challenge", callback_data="daily_challenge"),
                InlineKeyboardButton("👑 Premium", callback_data="premium_info")
            ],
            [
                InlineKeyboardButton("📊 My Stats", callback_data="user_stats"),
                InlineKeyboardButton("🎁 Referral Link", callback_data="referral_link")
            ],
            [
                InlineKeyboardButton("ℹ️ Help & Guide", callback_data="help_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_message = f"""
🎉 **Welcome to the World's Most Advanced Earning Bot!**

🎁 **Welcome Bonus:** +50 {CURRENCY} added to your account!

💰 **How to Earn:**
• Chat in approved groups: {MESSAGE_RATE} messages = 1 {CURRENCY}
• Complete daily challenges for bonus rewards
• Refer friends for massive bonuses
• Participate in competitions
• Unlock achievements for special rewards

🌟 **Advanced Features:**
• Dynamic earning multipliers
• VIP premium system
• Real-time leaderboards
• Anti-cheat protection
• Multi-level referral system

🚀 **Your Journey Starts Now!**
Choose an option below to explore:
        """
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
        
        # Notify referrer if applicable
        if referred_by:
            try:
                referrer = await db.get_user(referred_by)
                if referrer:
                    await context.bot.send_message(
                        chat_id=referred_by,
                        text=f"🎉 Great news! {user_name.get('first_name', 'Someone')} joined using your referral link!\n💰 You earned 25 {CURRENCY} bonus!"
                    )
            except:
                pass
    
    else:
        # Existing user - show dashboard
        current_balance = user.get('balance', 0)
        total_earnings = user.get('total_earnings', 0)
        user_level = user.get('user_level', 1)
        messages_today = await db.get_messages_today(user_id)
        
        # Check for daily login bonus
        daily_bonus = await economy_manager.process_daily_login(user_id)
        
        keyboard = [
            [
                InlineKeyboardButton("💰 Balance", callback_data="balance"),
                InlineKeyboardButton("📊 Stats", callback_data="user_stats")
            ],
            [
                InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
                InlineKeyboardButton("🎯 Challenges", callback_data="daily_challenge")
            ],
            [
                InlineKeyboardButton("💸 Withdraw", callback_data="withdraw_menu"),
                InlineKeyboardButton("👑 Premium", callback_data="premium_info")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        daily_bonus_text = f"\n🎁 Daily Login Bonus: +{daily_bonus} {CURRENCY}" if daily_bonus > 0 else ""
        
        dashboard_message = f"""
👋 **Welcome back, {user_name.get('first_name', 'User')}!**

💰 **Balance:** {int(current_balance)} {CURRENCY}
📈 **Total Earned:** {int(total_earnings)} {CURRENCY}
🎯 **Level:** {user_level}
📝 **Messages Today:** {messages_today}{daily_bonus_text}

🚀 **Ready to earn more?**
        """
        
        await update.message.reply_text(dashboard_message, reply_markup=reply_markup)

async def handle_start_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from start menu"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    await query.answer()
    
    if data == "balance":
        from plugins.balance import check_balance
        await check_balance(update, context)
    
    elif data == "user_stats":
        from plugins.stats import user_stats
        await user_stats(update, context)
    
    elif data == "leaderboard":
        from plugins.leaderboard import show_leaderboard
        await show_leaderboard(update, context)
    
    elif data == "daily_challenge":
        from plugins.challenges import show_daily_challenge
        await show_daily_challenge(update, context)
    
    elif data == "premium_info":
        from plugins.premium import show_premium_info
        await show_premium_info(update, context)
    
    elif data == "referral_link":
        from plugins.help import referral_command
        await referral_command(update, context)
    
    elif data == "help_menu":
        from plugins.help import help_command
        await help_command(update, context)
    
    elif data == "withdraw_menu":
        withdraw_text = f"""
💸 **Withdrawal Information**

💰 **Minimum:** {MIN_WITHDRAWAL} {CURRENCY}
📱 **Methods:** KPay, WavePay, AYAPay, CBPay
⏱️ **Processing:** 24-48 hours

📋 **To request withdrawal:**
Use command: `/withdraw <amount> <method> <phone>`

**Example:** `/withdraw 1000 kpay 09123456789`
        """
        await query.edit_message_text(withdraw_text)

def register_handlers(application: Application):
    """Register start command handlers"""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(handle_start_callbacks, pattern="^(balance|user_stats|leaderboard|daily_challenge|premium_info|referral_link|help_menu|withdraw_menu)$"))
