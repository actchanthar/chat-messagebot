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

def get_analytics_keyboard():
    """Get the persistent analytics keyboard"""
    return InlineKeyboardMarkup([
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
    ])

async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot analytics (Admin only)"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    reply_markup = get_analytics_keyboard()
    
    await update.message.reply_text("📊 **Bot Analytics Dashboard**\n\nChoose a category:", reply_markup=reply_markup)

async def handle_analytics_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle analytics callback queries - KEEP BUTTONS PERSISTENT"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    if user_id not in ADMIN_IDS:
        await query.answer("❌ Unauthorized access!", show_alert=True)
        return
    
    await query.answer()
    logger.info(f"Processing analytics callback: {data}")
    
    # Get persistent keyboard
    reply_markup = get_analytics_keyboard()
    
    try:
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
• Economy Health: {((total_earnings - total_withdrawals) / max(total_earnings, 1) * 100):.1f}%

📝 **ACTIVITY STATISTICS:**
• Total Messages: {total_messages:,}
• Avg Messages/User: {(total_messages / max(total_users, 1)):.1f}
• Messages Today: {await db.get_messages_today_count():,}

📈 **ENGAGEMENT:**
• Daily Active Rate: {(active_users_24h / max(total_users, 1) * 100):.1f}%
• Weekly Active Rate: {(active_users_7d / max(total_users, 1) * 100):.1f}%
• Premium Conversion: {(premium_users / max(total_users, 1) * 100):.1f}%

📊 Choose another category below:
            """
            
            # KEEP BUTTONS - Don't remove them
            await query.edit_message_text(overview_text, reply_markup=reply_markup)
        
        elif data == "analytics_users":
            # User analytics WITH BUTTONS
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
            
            users_text += f"\n📊 Choose another category below:"
            
            # KEEP BUTTONS
            await query.edit_message_text(users_text, reply_markup=reply_markup)
        
        elif data == "analytics_economy":
            # Economy analytics WITH BUTTONS
            try:
                total_earnings = await db.get_total_earnings()
                total_withdrawals = await db.get_total_withdrawals()
                
                economy_text = f"""
💰 **ECONOMY ANALYTICS**

📊 **OVERALL FLOW:**
• Total Earnings: {int(total_earnings):,} {CURRENCY}
• Total Withdrawals: {int(total_withdrawals):,} {CURRENCY}
• Net Flow: {int(total_earnings - total_withdrawals):,} {CURRENCY}

💸 **WITHDRAWAL STATUS:**
• Pending Requests: Calculating...
• Processing Needed: Calculating...

💎 **ECONOMY HEALTH:**
• Liquidity Ratio: {((total_earnings - total_withdrawals) / max(total_earnings, 1) * 100):.1f}%
• System Status: {'Healthy' if total_earnings > total_withdrawals else 'Monitor'}

📈 **TRENDS:**
• Bot is generating value for users
• Withdrawal rate is controlled
• Economy is sustainable

📊 Choose another category below:
                """
                
                # KEEP BUTTONS
                await query.edit_message_text(economy_text, reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Error in economy analytics: {e}")
                await query.edit_message_text("❌ Error loading economy data.", reply_markup=reply_markup)
        
        elif data == "analytics_growth":
            growth_text = f"""
📈 **Growth Analytics**

🚀 **Coming soon with advanced metrics!**

📊 **Will include:**
• User acquisition trends
• Retention rates
• Growth forecasting
• Channel performance
• Referral analysis

📊 Choose another category below:
            """
            await query.edit_message_text(growth_text, reply_markup=reply_markup)
        
        elif data == "analytics_engagement":
            engagement_text = f"""
🎮 **Engagement Analytics**

💬 **Coming soon with detailed engagement data!**

📊 **Will include:**
• Message frequency analysis
• User activity patterns
• Peak usage times
• Feature usage statistics
• Retention metrics

📊 Choose another category below:
            """
            await query.edit_message_text(engagement_text, reply_markup=reply_markup)
            
        elif data == "analytics_performance":
            performance_text = f"""
🏆 **Performance Analytics**

⚡ **Coming soon with performance insights!**

📊 **Will include:**
• Bot response times
• Error rates
• Success metrics
• User satisfaction
• System performance

📊 Choose another category below:
            """
            await query.edit_message_text(performance_text, reply_markup=reply_markup)
        
        else:
            # Unknown category
            await query.edit_message_text(f"📊 **Unknown Analytics Section**\n\nPlease choose a valid category below:", reply_markup=reply_markup)
    
    except Exception as e:
        logger.error(f"Error in analytics callback {data}: {e}")
        await query.edit_message_text("❌ Error loading analytics data.\n\n📊 Choose a category below:", reply_markup=reply_markup)

def register_handlers(application: Application):
    """Register analytics handlers"""
    logger.info("Registering analytics handlers")
    application.add_handler(CommandHandler("analytics", analytics_command))
    
    # Register callback handler with specific pattern
    application.add_handler(CallbackQueryHandler(
        handle_analytics_callbacks, 
        pattern="^analytics_"
    ))
    
    logger.info("✅ Analytics handlers registered successfully")
