from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest
import logging
import sys
import os
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import CURRENCY, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show leaderboard with category selection"""
    user_id = str(update.effective_user.id)
    logger.info(f"Leaderboard command by user {user_id}")
    
    try:
        # Create category selection keyboard
        keyboard = [
            [
                InlineKeyboardButton("💰 Top Earners", callback_data="lb_top_earners"),
                InlineKeyboardButton("💬 Most Active", callback_data="lb_messages")
            ],
            [
                InlineKeyboardButton("💳 Rich List", callback_data="lb_balance"),
                InlineKeyboardButton("💸 Big Withdrawers", callback_data="lb_withdrawals")
            ],
            [
                InlineKeyboardButton("👥 Best Inviters", callback_data="lb_referrals"),
                InlineKeyboardButton("📊 Bot Stats", callback_data="lb_stats")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            f"🏆 **LEADERBOARD & RANKINGS**\n\n"
            f"📈 **Choose a category to explore:**\n\n"
            f"💰 **Top Earners** - Highest total earnings\n"
            f"💬 **Most Active** - Users with most messages\n"
            f"💳 **Rich List** - Current highest balances\n"
            f"💸 **Big Withdrawers** - Successfully withdrew money\n"
            f"👥 **Best Inviters** - Top referral champions\n"
            f"📊 **Bot Stats** - Overall system statistics\n\n"
            f"🔥 **Compete and climb to the top!**\n"
            f"💪 **Your rank matters - keep earning!**"
        )
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in show_leaderboard: {e}")
        await update.message.reply_text("❌ Error loading leaderboard. Please try again later.")

def format_user_name(user: dict) -> str:
    """Format user name for display with Myanmar support"""
    try:
        first_name = user.get("first_name", "").strip()
        last_name = user.get("last_name", "").strip()
        username = user.get("username", "").strip()
        
        if first_name and last_name:
            full_name = f"{first_name} {last_name}"
        elif first_name:
            full_name = first_name
        elif username:
            full_name = f"@{username}"
        else:
            full_name = f"User{user.get('user_id', 'Unknown')[-4:]}"
        
        # Limit name length for display
        if len(full_name) > 15:
            full_name = full_name[:12] + "..."
        
        return full_name
        
    except Exception as e:
        logger.error(f"Error formatting user name: {e}")
        return "Unknown"

def get_rank_emoji(rank: int) -> str:
    """Get emoji for rank position"""
    rank_emojis = {
        1: "🥇",
        2: "🥈", 
        3: "🥉",
        4: "🏅",
        5: "🏅"
    }
    return rank_emojis.get(rank, f"{rank}.")

def format_number(number: int) -> str:
    """Format numbers with commas"""
    try:
        return f"{int(number):,}"
    except:
        return "0"

async def handle_leaderboard_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle leaderboard category selections"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    logger.info(f"Processing leaderboard callback: {data} from user {user_id}")
    
    try:
        await query.answer()
        
        # Create navigation keyboard
        keyboard = [
            [
                InlineKeyboardButton("💰 Earners", callback_data="lb_top_earners"),
                InlineKeyboardButton("💬 Active", callback_data="lb_messages")
            ],
            [
                InlineKeyboardButton("💳 Rich", callback_data="lb_balance"),
                InlineKeyboardButton("💸 Withdrawers", callback_data="lb_withdrawals")
            ],
            [
                InlineKeyboardButton("👥 Inviters", callback_data="lb_referrals"),
                InlineKeyboardButton("📊 Stats", callback_data="lb_stats")
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=data),
                InlineKeyboardButton("📈 My Rank", callback_data="lb_my_rank")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if data == "lb_top_earners":
            # Top earners leaderboard
            try:
                top_users = await db.get_leaderboard_data("total_earnings", 15)
                
                if not top_users:
                    text = "❌ No users found for earnings leaderboard."
                else:
                    text = f"💰 **TOP EARNERS HALL OF FAME**\n\n"
                    
                    for i, user in enumerate(top_users, 1):
                        name = format_user_name(user)
                        earnings = format_number(user.get("total_earnings", 0))
                        messages = format_number(user.get("messages", 0))
                        
                        rank_emoji = get_rank_emoji(i)
                        text += f"{rank_emoji} **{name}** - {earnings} {CURRENCY}\n"
                        text += f"     💬 {messages} messages\n\n"
                    
                    text += f"🏆 **{len(top_users)} champions displayed**\n"
                    text += f"💪 **Keep earning to join this elite list!**"
                    
            except Exception as e:
                logger.error(f"Error getting top earners: {e}")
                text = "❌ Error loading top earners. Please try again."
                
        elif data == "lb_messages":
            # Most active users leaderboard
            try:
                top_users = await db.get_leaderboard_data("messages", 15)
                
                if not top_users:
                    text = "❌ No active users found."
                else:
                    text = f"💬 **MOST ACTIVE CHATTERS**\n\n"
                    
                    for i, user in enumerate(top_users, 1):
                        name = format_user_name(user)
                        messages = format_number(user.get("messages", 0))
                        earnings = format_number(user.get("total_earnings", 0))
                        
                        rank_emoji = get_rank_emoji(i)
                        text += f"{rank_emoji} **{name}** - {messages} messages\n"
                        text += f"     💰 Earned {earnings} {CURRENCY}\n\n"
                    
                    text += f"💬 **{len(top_users)} most active users**\n"
                    text += f"🗣️ **Chat more to climb up!**"
                    
            except Exception as e:
                logger.error(f"Error getting most active: {e}")
                text = "❌ Error loading most active users."
                
        elif data == "lb_balance":
            # Highest balance leaderboard
            try:
                top_users = await db.get_leaderboard_data("balance", 15)
                
                if not top_users:
                    text = "❌ No users with balance found."
                else:
                    text = f"💳 **RICHEST USERS RIGHT NOW**\n\n"
                    
                    for i, user in enumerate(top_users, 1):
                        if user.get("balance", 0) <= 0:
                            continue
                            
                        name = format_user_name(user)
                        balance = format_number(user.get("balance", 0))
                        earnings = format_number(user.get("total_earnings", 0))
                        
                        rank_emoji = get_rank_emoji(i)
                        text += f"{rank_emoji} **{name}** - {balance} {CURRENCY}\n"
                        text += f"     📊 Total earned {earnings} {CURRENCY}\n\n"
                    
                    # Filter users with balance > 0
                    rich_users = [u for u in top_users if u.get("balance", 0) > 0]
                    text += f"💰 **{len(rich_users)} users have balance**\n"
                    text += f"💎 **Save money to get on this list!**"
                    
            except Exception as e:
                logger.error(f"Error getting richest users: {e}")
                text = "❌ Error loading balance leaderboard."
                
        elif data == "lb_withdrawals":
            # Top withdrawals leaderboard
            try:
                top_users = await db.get_leaderboard_data("total_withdrawn", 15)
                withdrawal_stats = await db.get_withdrawal_stats()
                
                # Filter users who actually withdrew
                withdrawers = [u for u in top_users if u.get("total_withdrawn", 0) > 0]
                
                if not withdrawers:
                    text = f"💸 **WITHDRAWAL CHAMPIONS**\n\n"
                    text += f"❌ **No withdrawals yet!**\n\n"
                    text += f"🎯 **Be the first to withdraw and get featured here!**\n"
                    text += f"💪 **Minimum withdrawal: 200 {CURRENCY}**\n"
                    text += f"🚀 **Start earning and make history!**"
                else:
                    text = f"💸 **WITHDRAWAL CHAMPIONS**\n\n"
                    
                    for i, user in enumerate(withdrawers, 1):
                        name = format_user_name(user)
                        withdrawn = format_number(user.get("total_withdrawn", 0))
                        earnings = format_number(user.get("total_earnings", 0))
                        
                        rank_emoji = get_rank_emoji(i)
                        text += f"{rank_emoji} **{name}** - {withdrawn} {CURRENCY} withdrawn\n"
                        text += f"     💰 Total earned {earnings} {CURRENCY}\n\n"
                    
                    text += f"💸 **{len(withdrawers)} successful withdrawers**\n"
                    text += f"📊 **Average withdrawal: {format_number(withdrawal_stats['avg_withdrawal'])} {CURRENCY}**\n"
                    text += f"🏆 **Earn and withdraw to join them!**"
                    
            except Exception as e:
                logger.error(f"Error getting withdrawal leaders: {e}")
                text = "❌ Error loading withdrawal leaderboard."
                
        elif data == "lb_referrals":
            # Best referrers leaderboard
            try:
                top_users = await db.get_leaderboard_data("successful_referrals", 15)
                
                # Filter users with referrals
                referrers = [u for u in top_users if u.get("successful_referrals", 0) > 0]
                
                if not referrers:
                    text = f"👥 **BEST REFERRAL CHAMPIONS**\n\n"
                    text += f"❌ **No referrals yet!**\n\n"
                    text += f"🎯 **Be the first to invite friends!**\n"
                    text += f"💰 **Get 50 {CURRENCY} per successful referral**\n"
                    text += f"🔗 **Share your link and earn more!**"
                else:
                    text = f"👥 **REFERRAL HALL OF FAME**\n\n"
                    
                    for i, user in enumerate(referrers, 1):
                        name = format_user_name(user)
                        referrals = format_number(user.get("successful_referrals", 0))
                        earnings = format_number(user.get("total_earnings", 0))
                        referral_earnings = user.get("successful_referrals", 0) * 50
                        
                        rank_emoji = get_rank_emoji(i)
                        text += f"{rank_emoji} **{name}** - {referrals} referrals\n"
                        text += f"     💰 Earned {format_number(referral_earnings)} {CURRENCY} from referrals\n\n"
                    
                    total_referrals = sum(u.get("successful_referrals", 0) for u in referrers)
                    text += f"👥 **{len(referrers)} active inviters**\n"
                    text += f"🎯 **{format_number(total_referrals)} total successful referrals**\n"
                    text += f"💪 **Invite friends to join this elite group!**"
                    
            except Exception as e:
                logger.error(f"Error getting referral leaders: {e}")
                text = "❌ Error loading referral leaderboard."
                
        elif data == "lb_stats":
            # Bot statistics
            try:
                stats = await db.get_user_stats_summary()
                withdrawal_stats = await db.get_withdrawal_stats()
                
                text = f"📊 **BOT STATISTICS DASHBOARD**\n\n"
                
                text += f"👥 **USER METRICS:**\n"
                text += f"• Total Users: {format_number(stats['total_users'])}\n"
                text += f"• Active Users: {format_number(stats['active_users'])}\n"
                text += f"• Banned Users: {format_number(stats['banned_users'])}\n\n"
                
                text += f"💰 **EARNINGS & FINANCE:**\n"
                text += f"• Total Distributed: {format_number(stats['total_earnings'])} {CURRENCY}\n"
                text += f"• Total Withdrawn: {format_number(stats['total_withdrawn'])} {CURRENCY}\n"
                text += f"• System Balance: {format_number(stats['system_balance'])} {CURRENCY}\n"
                text += f"• Total Withdrawers: {format_number(withdrawal_stats['total_withdrawers'])}\n\n"
                
                text += f"📈 **ACTIVITY METRICS:**\n"
                text += f"• Total Messages: {format_number(stats['total_messages'])}\n"
                
                if stats['active_users'] > 0:
                    avg_per_user = stats['total_earnings'] // stats['active_users']
                    msg_per_user = stats['total_messages'] // stats['active_users']
                    text += f"• Avg per User: {format_number(avg_per_user)} {CURRENCY}\n"
                    text += f"• Msg per User: {format_number(msg_per_user)}\n"
                
                text += f"\n⏰ **Updated:** {datetime.now().strftime('%H:%M')}\n"
                text += f"📅 **Date:** {datetime.now().strftime('%d/%m/%Y')}"
                
            except Exception as e:
                logger.error(f"Error getting bot stats: {e}")
                text = "❌ Error loading bot statistics. Please try again."
                
        elif data == "lb_my_rank":
            # User's personal ranking
            try:
                user = await db.get_user(user_id)
                if not user:
                    text = "❌ User not found. Please use /start first."
                else:
                    # Get user rankings
                    earnings_rank = await db.get_user_rank_by_earnings(user_id)
                    messages_rank = await db.get_user_rank(user_id, "messages")
                    balance_rank = await db.get_user_rank(user_id, "balance")
                    withdrawals_rank = await db.get_user_rank(user_id, "total_withdrawn")
                    referrals_rank = await db.get_user_rank(user_id, "successful_referrals")
                    
                    total_users = await db.get_total_users_count()
                    name = format_user_name(user)
                    
                    text = f"🏆 **YOUR PERSONAL RANKINGS**\n\n"
                    text += f"👤 **{name}**\n"
                    text += f"👥 **Out of {format_number(total_users)} users**\n\n"
                    
                    text += f"💰 **Earnings:** #{earnings_rank}\n"
                    text += f"     {format_number(user.get('total_earnings', 0))} {CURRENCY}\n\n"
                    
                    text += f"💬 **Messages:** #{messages_rank}\n"
                    text += f"     {format_number(user.get('messages', 0))} messages\n\n"
                    
                    text += f"💳 **Balance:** #{balance_rank}\n"
                    text += f"     {format_number(user.get('balance', 0))} {CURRENCY}\n\n"
                    
                    text += f"💸 **Withdrawals:** #{withdrawals_rank}\n"
                    text += f"     {format_number(user.get('total_withdrawn', 0))} {CURRENCY}\n\n"
                    
                    text += f"👥 **Referrals:** #{referrals_rank}\n"
                    text += f"     {format_number(user.get('successful_referrals', 0))} friends\n\n"
                    
                    # Add motivational message
                    if earnings_rank <= 3:
                        text += f"🔥 **TOP 3 EARNER! You're amazing!**"
                    elif earnings_rank <= 10:
                        text += f"⭐ **TOP 10! Keep climbing!**"
                    elif earnings_rank <= 50:
                        text += f"💪 **TOP 50! You're doing great!**"
                    else:
                        text += f"🚀 **Chat more to climb the ranks!**"
                        
            except Exception as e:
                logger.error(f"Error getting user rank: {e}")
                text = "❌ Error loading your rankings."
        
        else:
            text = "❌ Unknown leaderboard category."
        
        # Try to edit message, handle "message not modified" error
        try:
            await query.edit_message_text(text, reply_markup=reply_markup)
        except BadRequest as e:
            if "Message is not modified" in str(e):
                # Message content is the same, just ignore
                pass
            else:
                # Other BadRequest error, re-raise
                raise e
        
    except Exception as e:
        logger.error(f"Error processing leaderboard callback {data}: {e}")
        
        # Create fallback keyboard
        keyboard = [
            [
                InlineKeyboardButton("💰 Top Earners", callback_data="lb_top_earners"),
                InlineKeyboardButton("💬 Most Active", callback_data="lb_messages")
            ],
            [
                InlineKeyboardButton("📊 Bot Stats", callback_data="lb_stats"),
                InlineKeyboardButton("🔄 Try Again", callback_data="lb_top_earners")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text("❌ Error loading leaderboard\n\n🏆 Please select a category:", reply_markup=reply_markup)
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                logger.error(f"Failed to edit message after error: {e}")

async def my_rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's personal ranking - shortcut command"""
    user_id = str(update.effective_user.id)
    logger.info(f"My rank command by user {user_id}")
    
    try:
        # Get user data
        user = await db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found. Please use /start first.")
            return
        
        # Get user rankings
        earnings_rank = await db.get_user_rank_by_earnings(user_id)
        messages_rank = await db.get_user_rank(user_id, "messages")
        balance_rank = await db.get_user_rank(user_id, "balance")
        total_users = await db.get_total_users_count()
        
        # Format user name
        name = format_user_name(user)
        
        rank_text = f"🏆 **YOUR CURRENT RANKING**\n\n"
        rank_text += f"👤 **{name}**\n\n"
        
        rank_text += f"💰 **Earnings Rank:** #{earnings_rank}/{format_number(total_users)}\n"
        rank_text += f"💳 **Balance:** {format_number(user.get('balance', 0))} {CURRENCY}\n"
        rank_text += f"📊 **Total Earned:** {format_number(user.get('total_earnings', 0))} {CURRENCY}\n\n"
        
        rank_text += f"💬 **Activity Rank:** #{messages_rank}/{format_number(total_users)}\n"
        rank_text += f"📝 **Messages Sent:** {format_number(user.get('messages', 0))}\n\n"
        
        # Add performance indicator
        if earnings_rank <= 10:
            rank_text += f"🔥 **ELITE PERFORMER!**\n"
        elif earnings_rank <= 50:
            rank_text += f"⭐ **GREAT PERFORMANCE!**\n"
        else:
            rank_text += f"💪 **KEEP CLIMBING!**\n"
        
        rank_text += f"🚀 **Chat more to improve your rank!**"
        
        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("🏆 Full Leaderboard", callback_data="lb_top_earners"),
                InlineKeyboardButton("📊 Detailed Stats", callback_data="lb_my_rank")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(rank_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in my_rank: {e}")
        await update.message.reply_text("❌ Error loading your ranking. Please try again later.")

def register_handlers(application: Application):
    """Register leaderboard command handlers"""
    logger.info("Registering leaderboard handlers")
    
    # Command handlers
    application.add_handler(CommandHandler("leaderboard", show_leaderboard))
    application.add_handler(CommandHandler("lb", show_leaderboard))
    application.add_handler(CommandHandler("top", show_leaderboard))
    application.add_handler(CommandHandler("rank", my_rank))
    application.add_handler(CommandHandler("myrank", my_rank))
    application.add_handler(CommandHandler("stats", show_leaderboard))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(
        handle_leaderboard_callbacks, 
        pattern=r"^lb_"
    ))
    
    logger.info("✅ Leaderboard handlers registered successfully")
