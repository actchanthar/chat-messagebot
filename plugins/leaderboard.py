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
from config import CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show top users leaderboard"""
    keyboard = [
        [
            InlineKeyboardButton("💰 Top Earners", callback_data="top_earners"),
            InlineKeyboardButton("📝 Top Messages", callback_data="top_messages")
        ],
        [
            InlineKeyboardButton("👥 Top Referrers", callback_data="top_referrers"),
            InlineKeyboardButton("🏆 Today's Leaders", callback_data="top_today")
        ],
        [
            InlineKeyboardButton("🎯 Weekly Champions", callback_data="top_weekly"),
            InlineKeyboardButton("👑 VIP Members", callback_data="top_vip")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("🏆 **Choose Leaderboard Type:**", reply_markup=reply_markup)

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show main leaderboard"""
    query = update.callback_query
    if query:
        await query.answer()
    
    # Get top users by different categories
    top_earners = await db.get_top_users(10, "total_earnings")
    top_messages = await db.get_top_users(10, "messages")
    top_referrers = await db.get_top_users(10, "successful_referrals")
    
    leaderboard_text = """
🏆 **LEADERBOARD - TOP PERFORMERS**

💰 **TOP EARNERS:**
"""
    
    for i, user in enumerate(top_earners[:5], 1):
        total_earnings = user.get('total_earnings', 0)
        name = user.get('first_name', 'Unknown')[:15]
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        leaderboard_text += f"{medal} {name} - {int(total_earnings)} {CURRENCY}\n"
    
    leaderboard_text += f"""
📝 **TOP MESSAGERS:**
"""
    
    for i, user in enumerate(top_messages[:5], 1):
        messages = user.get('messages', 0)
        name = user.get('first_name', 'Unknown')[:15]
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        leaderboard_text += f"{medal} {name} - {messages:,} msgs\n"
    
    leaderboard_text += f"""
👥 **TOP REFERRERS:**
"""
    
    for i, user in enumerate(top_referrers[:5], 1):
        referrals = user.get('successful_referrals', 0)
        name = user.get('first_name', 'Unknown')[:15]
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        leaderboard_text += f"{medal} {name} - {referrals} refs\n"
    
    # Add competitive elements
    leaderboard_text += f"""
🎯 **COMPETE & WIN:**
• Top 3 earners get daily bonuses!
• Weekly competitions with mega prizes!
• Referral contests with special rewards!
    """
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="leaderboard"),
            InlineKeyboardButton("📊 My Rank", callback_data="my_rank")
        ],
        [
            InlineKeyboardButton("🎯 Join Competition", callback_data="join_competition")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(leaderboard_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(leaderboard_text, reply_markup=reply_markup)

async def handle_leaderboard_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle leaderboard callback queries"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    await query.answer()
    
    if data == "my_rank":
        user = await db.get_user(user_id)
        if user:
            # Calculate user rankings
            total_users = await db.get_total_users_count()
            earning_rank = await db.get_user_rank(user_id, "total_earnings")
            message_rank = await db.get_user_rank(user_id, "messages")
            
            rank_text = f"""
📊 **YOUR RANKINGS**

💰 **Earning Rank:** #{earning_rank} out of {total_users}
📝 **Message Rank:** #{message_rank} out of {total_users}
🎯 **Level:** {user.get('user_level', 1)}
📈 **Progress:** {user.get('total_earnings', 0)} {CURRENCY} earned

🚀 **Keep going to climb higher!**
            """
            await query.edit_message_text(rank_text)
    
    elif data == "join_competition":
        competition_text = """
🎯 **ACTIVE COMPETITIONS**

🏆 **Weekly Earning Challenge**
• Duration: Monday to Sunday
• Prize: 1000 {CURRENCY} for #1
• Top 10 get bonus rewards!

👥 **Referral Contest**
• Refer most users this week
• Winner gets 2000 {CURRENCY}
• All participants get bonuses!

🎮 **Daily Message Challenge**
• Send 100 messages today
• Earn 2x multiplier bonus!

Join now and start competing!
        """
        await query.edit_message_text(competition_text)

def register_handlers(application: Application):
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("leaderboard", show_leaderboard))
    application.add_handler(CallbackQueryHandler(handle_leaderboard_callbacks, pattern="^(leaderboard|my_rank|join_competition|top_)"))
