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

def get_leaderboard_keyboard():
    """Get the persistent leaderboard keyboard"""
    return InlineKeyboardMarkup([
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
        ],
        [
            InlineKeyboardButton("📊 My Rank", callback_data="my_rank"),
            InlineKeyboardButton("🎮 Join Competition", callback_data="join_competition")
        ]
    ])

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show top users leaderboard MENU first"""
    
    # Show menu with buttons - don't jump to specific leaderboard
    menu_text = """
🏆 **LEADERBOARD MENU**

📊 **Choose what you want to see:**

💰 **Top Earners** - Highest total earnings
📝 **Top Messages** - Most active chatters  
👥 **Top Referrers** - Best inviters
🏆 **Today's Leaders** - Today's top performers
🎯 **Weekly Champions** - This week's winners
👑 **VIP Members** - Premium users only

📈 **Personal:**
📊 **My Rank** - See your rankings
🎮 **Join Competition** - Active contests

🎯 **Select a category below:**
    """
    
    reply_markup = get_leaderboard_keyboard()
    await update.message.reply_text(menu_text, reply_markup=reply_markup)

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show main combined leaderboard (for /leaderboard command)"""
    query = update.callback_query
    if query:
        await query.answer()
    
    # Get top users by different categories
    top_earners = await db.get_top_users(5, "total_earnings")
    top_messages = await db.get_top_users(5, "messages")
    top_referrers = await db.get_top_users(5, "successful_referrals")
    
    leaderboard_text = """
🏆 **COMBINED LEADERBOARD**

💰 **TOP EARNERS:**
"""
    
    for i, user in enumerate(top_earners, 1):
        total_earnings = user.get('total_earnings', 0)
        name = user.get('first_name', 'Unknown')[:15]
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        leaderboard_text += f"{medal} {name} - {int(total_earnings)} {CURRENCY}\n"
    
    leaderboard_text += f"""
📝 **TOP MESSAGERS:**
"""
    
    for i, user in enumerate(top_messages, 1):
        messages = user.get('messages', 0)
        name = user.get('first_name', 'Unknown')[:15]
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        leaderboard_text += f"{medal} {name} - {messages:,} msgs\n"
    
    leaderboard_text += f"""
👥 **TOP REFERRERS:**
"""
    
    for i, user in enumerate(top_referrers, 1):
        referrals = user.get('successful_referrals', 0)
        name = user.get('first_name', 'Unknown')[:15]
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        leaderboard_text += f"{medal} {name} - {referrals} refs\n"
    
    leaderboard_text += f"""
🎯 **Select a specific category below:**
    """
    
    reply_markup = get_leaderboard_keyboard()
    
    if query:
        await query.edit_message_text(leaderboard_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(leaderboard_text, reply_markup=reply_markup)

async def handle_leaderboard_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle leaderboard callback queries - KEEP BUTTONS PERSISTENT"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    await query.answer()
    logger.info(f"Processing leaderboard callback: {data} from user {user_id}")
    
    # Get persistent keyboard
    reply_markup = get_leaderboard_keyboard()
    
    try:
        if data == "leaderboard":
            await show_leaderboard(update, context)
        
        elif data == "my_rank":
            user = await db.get_user(user_id)
            if user:
                # Calculate user rankings
                total_users = await db.get_total_users_count()
                earning_rank = await db.get_user_rank(user_id, "total_earnings")
                message_rank = await db.get_user_rank(user_id, "messages")
                
                rank_text = f"""
📊 **YOUR RANKINGS**

👤 **Your Profile:**
• Name: {user.get('first_name', 'Unknown')} {user.get('last_name', '')}
• Level: {user.get('user_level', 1)}

🏆 **Your Rankings:**
• 💰 Earning Rank: #{earning_rank} out of {total_users}
• 📝 Message Rank: #{message_rank} out of {total_users}

📈 **Your Stats:**
• Balance: {int(user.get('balance', 0))} {CURRENCY}
• Total Earned: {int(user.get('total_earnings', 0))} {CURRENCY}
• Messages: {user.get('messages', 0):,}
• Referrals: {user.get('successful_referrals', 0)}

🚀 Keep going to climb higher!

🏆 **Select another category below:**
                """
                # KEEP BUTTONS
                await query.edit_message_text(rank_text, reply_markup=reply_markup)
            else:
                await query.edit_message_text("❌ User not found\n\n🏆 Select a category below:", reply_markup=reply_markup)
        
        elif data == "join_competition":
            competition_text = f"""
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

📊 **Monthly Leaderboard**
• Compete for the monthly crown
• Grand prize: 5000 {CURRENCY}

🔥 Join now and start competing!

🏆 **Select another category below:**
            """
            # KEEP BUTTONS
            await query.edit_message_text(competition_text, reply_markup=reply_markup)
        
        elif data.startswith("top_"):
            # Handle specific leaderboard types
            category = data.replace("top_", "")
            
            if category == "earners":
                top_users = await db.get_top_users(15, "total_earnings")
                title = "💰 **TOP EARNERS LEADERBOARD**"
                field = "total_earnings"
                suffix = CURRENCY
            elif category == "messages":
                top_users = await db.get_top_users(15, "messages")
                title = "📝 **TOP MESSAGERS LEADERBOARD**"
                field = "messages"
                suffix = "msgs"
            elif category == "referrers":
                top_users = await db.get_top_users(15, "successful_referrals")
                title = "👥 **TOP REFERRERS LEADERBOARD**"
                field = "successful_referrals"
                suffix = "refs"
            elif category == "today":
                # Show today's top performers (simplified)
                top_users = await db.get_top_users(10, "messages")  # Using messages as proxy for today
                title = "🏆 **TODAY'S TOP PERFORMERS**"
                field = "messages"
                suffix = "msgs today"
            elif category == "weekly":
                # Show weekly champions (simplified) 
                top_users = await db.get_top_users(10, "total_earnings")
                title = "🎯 **WEEKLY CHAMPIONS**"
                field = "total_earnings"
                suffix = f"{CURRENCY} this week"
            elif category == "vip":
                # Show VIP/Premium members
                all_users = await db.get_all_users()
                vip_users = [user for user in all_users if user.get('is_premium', False)][:10]
                title = "👑 **VIP MEMBERS LEADERBOARD**"
                
                if vip_users:
                    leaderboard_text = f"{title}\n\n"
                    for i, user in enumerate(vip_users, 1):
                        name = user.get('first_name', 'Unknown')[:15]
                        earnings = user.get('total_earnings', 0)
                        medal = "👑" if i == 1 else "💎" if i == 2 else "💍" if i == 3 else f"{i}."
                        leaderboard_text += f"{medal} {name} - {int(earnings)} {CURRENCY} (VIP)\n"
                else:
                    leaderboard_text = f"{title}\n\n🔒 No VIP members yet!\n\nBecome the first VIP member!"
                
                leaderboard_text += f"\n\n🏆 **Select another category below:**"
                await query.edit_message_text(leaderboard_text, reply_markup=reply_markup)
                return
            else:
                await query.edit_message_text(f"🏆 **{category.title()} Leaderboard**\n\nComing soon!\n\n🏆 Select another category below:", reply_markup=reply_markup)
                return
            
            leaderboard_text = f"{title}\n\n"
            
            for i, user in enumerate(top_users, 1):
                name = user.get('first_name', 'Unknown')[:15]
                value = user.get(field, 0)
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                
                if field == "total_earnings":
                    leaderboard_text += f"{medal} {name} - {int(value)} {suffix}\n"
                else:
                    leaderboard_text += f"{medal} {name} - {value:,} {suffix}\n"
            
            leaderboard_text += f"\n🏆 **Select another category below:**"
            
            # KEEP BUTTONS for specific categories
            await query.edit_message_text(leaderboard_text, reply_markup=reply_markup)
        
        else:
            await query.edit_message_text(f"❌ Unknown leaderboard action\n\n🏆 Select a category below:", reply_markup=reply_markup)
    
    except Exception as e:
        logger.error(f"Error processing leaderboard callback {data}: {e}")
        await query.edit_message_text("❌ Error loading leaderboard\n\n🏆 Select a category below:", reply_markup=reply_markup)

def register_handlers(application: Application):
    """Register leaderboard handlers"""
    logger.info("Registering leaderboard handlers")
    application.add_handler(CommandHandler("top", top_command))  # Shows MENU first
    application.add_handler(CommandHandler("leaderboard", show_leaderboard))  # Shows combined view
    
    # Register callback handler with ALL patterns
    application.add_handler(CallbackQueryHandler(
        handle_leaderboard_callbacks, 
        pattern="^(leaderboard|my_rank|join_competition|top_)"
    ))
    
    logger.info("✅ Leaderboard handlers registered successfully")
