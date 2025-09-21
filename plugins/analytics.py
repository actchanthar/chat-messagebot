from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import CURRENCY, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot analytics (Admin only)"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Overview", callback_data="analytics_overview"),
            InlineKeyboardButton("👥 Users", callback_data="analytics_users")
        ],
        [
            InlineKeyboardButton("💰 Economy", callback_data="analytics_economy"),
            InlineKeyboardButton("📈 Growth", callback_data="analytics_growth")
        ],
        [
            InlineKeyboardButton("🎮 Engagement", callback_data="analytics_engagement"),
            InlineKeyboardButton("🏆 Performance", callback_data="analytics_performance")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("📊 **Bot Analytics Dashboard**\n\nChoose a category:", reply_markup=reply_markup)

async def handle_analytics_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle analytics callback queries"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    if user_id not in ADMIN_IDS:
        await query.answer("❌ Unauthorized access!")
        return
    
    await query.answer()
    
    if data == "analytics_overview":
        # Get comprehensive bot statistics
        total_users = await db.get_total_users_count()
        active_users_24h = await db.get_active_users_count(24)
        active_users_7d = await db.get_active_users_count(168)
        total_messages = await db.get_total_messages_count()
        total_earnings = await db.get_total_earnings()
        total_withdrawals = await db.get_total_withdrawals()
        premium_users = await db.get_premium_users_count()
        banned_users = await db.get_banned_users_count()
        
        overview_text = f"""
📊 **BOT OVERVIEW ANALYTICS**

👥 **USER STATISTICS:**
• Total Users: {total_users:,}
• Active (24h): {active_users_24h:,}
• Active (7d): {active_users_7d:,}
• Premium Users: {premium_users:,}
• Banned Users: {banned_users:,}

💰 **ECONOMY STATISTICS:**
• Total Earned: {int(total_earnings):,} {CURRENCY}
• Total Withdrawn: {int(total_withdrawals):,} {CURRENCY}
• Economy Health: {((total_earnings - total_withdrawals) / total_earnings * 100):.1f}%

📝 **ACTIVITY STATISTICS:**
• Total Messages: {total_messages:,}
• Avg Messages/User: {(total_messages / total_users):.1f}
• Messages Today: {await db.get_messages_today_count():,}

📈 **ENGAGEMENT:**
• Daily Active Rate: {(active_users_24h / total_users * 100):.1f}%
• Weekly Active Rate: {(active_users_7d / total_users * 100):.1f}%
• Premium Conversion: {(premium_users / total_users * 100):.1f}%
        """
        
        await query.edit_message_text(overview_text)
    
    elif data == "analytics_users":
        # User analytics
        new_users_today = await db.get_new_users_count(1)
        new_users_week = await db.get_new_users_count(7)
        new_users_month = await db.get_new_users_count(30)
        top_earners = await db.get_top_users(5, "total_earnings")
        top_referrers = await db.get_top_users(5, "successful_referrals")
        
        users_text = f"""
👥 **USER ANALYTICS**

📈 **GROWTH METRICS:**
• New Users Today: {new_users_today:,}
• New Users (7d): {new_users_week:,}
• New Users (30d): {new_users_month:,}
• Growth Rate: {(new_users_week / 7):.1f} users/day

🏆 **TOP PERFORMERS:**

💰 **Top Earners:**
"""
        
        for i, user in enumerate(top_earners, 1):
            name = user.get('first_name', 'Unknown')[:15]
            earnings = user.get('total_earnings', 0)
            users_text += f"{i}. {name}: {int(earnings)} {CURRENCY}\n"
        
        users_text += f"""
👥 **Top Referrers:**
"""
        
        for i, user in enumerate(top_referrers, 1):
            name = user.get('first_name', 'Unknown')[:15]
            referrals = user.get('successful_referrals', 0)
            users_text += f"{i}. {name}: {referrals} referrals\n"
        
        await query.edit_message_text(users_text)
    
    elif data == "analytics_economy":
        # Economy analytics
        daily_earnings = await db.get_daily_earnings()
        daily_withdrawals = await db.get_daily_withdrawals()
        pending_withdrawals = await db.get_pending_withdrawals_count()
        premium_revenue = await db.get_premium_revenue()
        
        economy_text = f"""
💰 **ECONOMY ANALYTICS**

📊 **DAILY FLOW:**
• Today's Earnings: {int(daily_earnings):,} {CURRENCY}
• Today's Withdrawals: {int(daily_withdrawals):,} {CURRENCY}
• Net Flow: {int(daily_earnings - daily_withdrawals):,} {CURRENCY}

💸 **WITHDRAWAL STATUS:**
• Pending Requests: {pending_withdrawals:,}
• Processing Needed: {await db.get_pending_withdrawal_amount():,} {CURRENCY}

💎 **PREMIUM REVENUE:**
• Total Premium Sales: {int(premium_revenue):,} {CURRENCY}
• Active Premium Users: {await db.get_premium_users_count():,}

🏦 **ECONOMY HEALTH:**
• Liquidity Ratio: {((daily_earnings - daily_withdrawals) / daily_earnings * 100):.1f}%
• User Satisfaction: {await db.get_user_satisfaction_rate():.1f}%
        """
        
        await query.edit_message_text(economy_text)

def register_handlers(application: Application):
    application.add_handler(CommandHandler("analytics", analytics_command))
    application.add_handler(CallbackQueryHandler(handle_analytics_callbacks, pattern="^analytics_"))
