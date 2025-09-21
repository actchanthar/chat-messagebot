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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """WORLD'S MOST ADVANCED START COMMAND"""
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Advanced start command by user {user_id}")

    # Check for referral with advanced tracking
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

    # Advanced subscription check
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

        # Add check subscription button
        keyboard.append([InlineKeyboardButton("✅ I've Joined All Channels", callback_data="check_subscription")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🔐 **Subscription Required**\n\n"
            "Please join ALL channels below to use the bot:\n"
            "ကျေးဇူးပြု၍ အောက်ပါချန်နယ်များသို့ဝင်ရောက်ပါ။\n\n"
            "💰 **After joining, you can earn money by chatting!**",
            reply_markup=reply_markup
        )
        return

    # Get or create user with advanced features
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
        welcome_bonus = 100  # Increased welcome bonus!
        await db.add_bonus(user_id, welcome_bonus)
        logger.info(f"New user {user_id} created with {welcome_bonus} {CURRENCY} bonus")

        # Process referral rewards (ENHANCED)
        if referred_by:
            referrer = await db.get_user(referred_by)
            if referrer and not referrer.get("banned", False):
                # Multi-level referral system
                referral_reward = await db.get_referral_reward()  # Base reward
                bonus_multiplier = 1
                
                # Check referrer level for bonus multiplier
                referrer_level = referrer.get("user_level", 1)
                if referrer_level >= 5:
                    bonus_multiplier = 1.5  # 50% bonus for level 5+
                elif referrer_level >= 3:
                    bonus_multiplier = 1.25  # 25% bonus for level 3+
                
                final_reward = int(referral_reward * bonus_multiplier)
                
                # Update referrer stats
                current_balance = referrer.get("balance", 0)
                new_invites = referrer.get("invites", 0) + 1
                successful_referrals = referrer.get("successful_referrals", 0) + 1
                
                await db.update_user(referred_by, {
                    "balance": current_balance + final_reward,
                    "invites": new_invites,
                    "successful_referrals": successful_referrals
                })
                
                # Notify referrer with advanced message
                try:
                    referrer_name = update.effective_user.first_name or "Someone"
                    await context.bot.send_message(
                        chat_id=referred_by,
                        text=f"🎉 **New Referral Success!**\n\n"
                             f"👤 **{referrer_name}** joined using your link!\n"
                             f"💰 **Reward:** +{final_reward} {CURRENCY}\n"
                             f"📊 **Total Referrals:** {successful_referrals}\n"
                             f"💳 **New Balance:** {int(current_balance + final_reward)} {CURRENCY}\n\n"
                             f"🚀 **Level {referrer_level} Bonus Applied!**" if bonus_multiplier > 1 else ""
                    )
                except Exception as e:
                    logger.error(f"Failed to notify referrer {referred_by}: {e}")

    # Get user stats for dashboard
    current_balance = user.get("balance", 0)
    total_messages = user.get("messages", 0) 
    user_level = user.get("user_level", 1)
    total_earnings = user.get("total_earnings", 0)
    successful_referrals = user.get("successful_referrals", 0)

    # Create ADVANCED welcome message
    if is_new_user:
        welcome_message = (
            f"🎉 **Welcome to the World's Most Advanced Earning Bot!**\n\n"
            f"👋 **Hello {update.effective_user.first_name}!**\n\n"
            f"🎁 **Welcome Bonus:** +{welcome_bonus} {CURRENCY} added!\n"
            f"💰 **Your Balance:** {int(current_balance)} {CURRENCY}\n\n"
            f"💎 **How to Earn:**\n"
            f"• Chat in approved groups: 3 messages = 1 {CURRENCY}\n"
            f"• Refer friends for massive bonuses\n"
            f"• Complete daily challenges\n"
            f"• Participate in competitions\n\n"
            f"🚀 **Advanced Features:**\n"
            f"• Real-time leaderboards\n"
            f"• Achievement system\n"
            f"• VIP premium memberships\n"
            f"• Multi-level referral rewards\n"
            f"• Anti-cheat protection\n\n"
        )
    else:
        # Returning user dashboard
        welcome_message = (
            f"👋 **Welcome back, {update.effective_user.first_name}!**\n\n"
            f"📊 **Your Dashboard:**\n"
            f"💰 Balance: **{int(current_balance)} {CURRENCY}**\n"
            f"📝 Messages: **{total_messages:,}**\n"
            f"🎯 Level: **{user_level}**\n"
            f"💸 Total Earned: **{int(total_earnings)} {CURRENCY}**\n"
            f"👥 Referrals: **{successful_referrals}**\n\n"
        )

    # Add ADVANCED leaderboard (Top 10 with enhanced display)
    try:
        users = await db.get_all_users()
        if users and len(users) >= 3:
            # Get top users by different categories
            top_earners = sorted(users, key=lambda x: x.get("total_earnings", 0), reverse=True)[:10]
            top_messagers = sorted(users, key=lambda x: x.get("messages", 0), reverse=True)[:5]
            
            if top_earners and top_earners[0].get("total_earnings", 0) > 0:
                phone_bill_reward = await db.get_phone_bill_reward()
                message_rate = await db.get_message_rate()
                
                # Enhanced leaderboard with emojis and formatting
                leaderboard_message = (
                    f"🏆 **LEADERBOARD - TOP EARNERS**\n"
                    f"💎 (Top 3 get weekly rewards: {phone_bill_reward})\n\n"
                )
                
                for i, top_user in enumerate(top_earners[:10], 1):
                    name = (top_user.get('first_name', 'Unknown') + ' ' + top_user.get('last_name', '')).strip()[:20]
                    earnings = top_user.get("total_earnings", 0)
                    messages = top_user.get("messages", 0)
                    level = top_user.get("user_level", 1)
                    
                    # Enhanced medals and formatting
                    if i == 1:
                        medal = "👑"
                        name_format = f"**{name}**"
                    elif i == 2:
                        medal = "🥈"
                        name_format = f"**{name}**"
                    elif i == 3:
                        medal = "🥉"
                        name_format = f"**{name}**"
                    else:
                        medal = f"{i}."
                        name_format = name
                    
                    leaderboard_message += f"{medal} {name_format} - {int(earnings)} {CURRENCY} | Lv.{level}\n"
                
                # Add current earning rate
                leaderboard_message += (
                    f"\n📊 **Current Rate:** {message_rate} messages = 1 {CURRENCY}\n"
                    f"🎯 **Active Users:** {len([u for u in users if u.get('messages', 0) > 0]):,}\n"
                )
                
                welcome_message += leaderboard_message
    
    except Exception as e:
        logger.error(f"Error generating leaderboard: {e}")

    # Add bot info and links
    welcome_message += (
        f"\n🔗 **Your Referral Link:**\n"
        f"`https://t.me/{context.bot.username}?start=ref_{user_id}`\n\n"
        f"👨‍💻 **Developer:** @When_the_night_falls_my_soul_se\n"
        f"📢 **Updates:** https://t.me/ITAnimeAI\n\n"
        f"🎮 **Use buttons below for advanced features!**"
    )

    # ADVANCED interactive keyboard with more features
    keyboard = [
        [
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("📊 My Stats", callback_data="detailed_stats")
        ],
        [
            InlineKeyboardButton("🏆 Leaderboard", callback_data="advanced_leaderboard"),
            InlineKeyboardButton("💸 Withdraw", callback_data="withdrawal_menu")
        ],
        [
            InlineKeyboardButton("🎯 Daily Challenge", callback_data="daily_challenges"),
            InlineKeyboardButton("👑 Premium", callback_data="premium_features")
        ],
        [
            InlineKeyboardButton("👥 Referral Hub", callback_data="referral_center"),
            InlineKeyboardButton("🎁 Achievements", callback_data="achievements")
        ],
        [
            InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/When_the_night_falls_my_soul_se"),
            InlineKeyboardButton("📢 Updates", url="https://t.me/ITAnimeAI")
        ],
        [
            InlineKeyboardButton("💬 Join Earning Group", url="https://t.me/stranger77777777777")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="Markdown")
        logger.info(f"Advanced welcome message sent to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send welcome message: {e}")
        # Fallback without markdown
        await update.message.reply_text(welcome_message.replace("**", "").replace("*", ""), reply_markup=reply_markup)

async def handle_start_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle advanced start menu callbacks"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    await query.answer()
    
    if data == "check_subscription":
        # Re-check subscription
        subscribed, not_subscribed = await check_subscription(context, int(user_id), query.message.chat_id)
        if subscribed:
            await query.edit_message_text("✅ **Subscription Verified!**\n\nWelcome to the earning bot! Use /start to begin.")
        else:
            await query.answer("❌ Please join ALL channels first!", show_alert=True)
    
    elif data == "balance":
        user = await db.get_user(user_id)
        if user:
            balance = user.get("balance", 0)
            total_earned = user.get("total_earnings", 0)
            await query.edit_message_text(
                f"💰 **Your Financial Summary**\n\n"
                f"💳 **Current Balance:** {int(balance)} {CURRENCY}\n"
                f"📈 **Total Earned:** {int(total_earned)} {CURRENCY}\n"
                f"💸 **Available to Withdraw:** {int(balance)} {CURRENCY}\n\n"
                f"သင့်လက်ကျန်ငွေ: {int(balance)} ကျပ်\n\n"
                f"💡 **Keep chatting in groups to earn more!**"
            )
    
    elif data == "detailed_stats":
        user = await db.get_user(user_id)
        if user:
            # Calculate additional stats
            messages_today = await db.get_user_messages_today(user_id)
            rank = await db.get_user_rank_by_earnings(user_id)
            
            stats_text = f"""
📊 **ADVANCED USER STATISTICS**

👤 **Profile:**
• Name: {user.get('first_name', 'Unknown')} {user.get('last_name', '')}
• Level: {user.get('user_level', 1)}
• Rank: #{rank}

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

🎯 **Achievements:** {len(user.get('achievements', []))} unlocked
            """
            await query.edit_message_text(stats_text)
    
    elif data == "advanced_leaderboard":
        # Show advanced leaderboard with tabs
        keyboard = [
            [
                InlineKeyboardButton("💰 Top Earners", callback_data="lb_earners"),
                InlineKeyboardButton("📝 Top Messages", callback_data="lb_messages")
            ],
            [
                InlineKeyboardButton("👥 Top Referrers", callback_data="lb_referrers"),
                InlineKeyboardButton("📈 This Week", callback_data="lb_weekly")
            ],
            [
                InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🏆 **ADVANCED LEADERBOARDS**\n\n"
            "Choose which leaderboard to view:\n"
            "• 💰 **Top Earners** - Highest total earnings\n"
            "• 📝 **Top Messages** - Most active chatters\n" 
            "• 👥 **Top Referrers** - Best inviters\n"
            "• 📈 **This Week** - Weekly champions\n\n"
            "🎯 **Compete with thousands of users!**",
            reply_markup=reply_markup
        )
    
    elif data == "daily_challenges":
        await query.edit_message_text(
            "🎯 **DAILY CHALLENGES**\n\n"
            "💎 **Coming Soon!**\n\n"
            "Advanced daily challenge system with:\n"
            "• Dynamic difficulty based on your level\n"
            "• Massive reward bonuses\n"
            "• Streak multipliers\n"
            "• Special achievements\n\n"
            "🚀 **Stay tuned for incredible earning opportunities!**"
        )
    
    elif data == "premium_features":
        await query.edit_message_text(
            "👑 **PREMIUM VIP FEATURES**\n\n"
            "💎 **Unlock Premium Benefits:**\n"
            "• 2x Earning multiplier\n"
            "• Instant withdrawals\n"
            "• Exclusive challenges\n"
            "• VIP support priority\n"
            "• Premium-only competitions\n"
            "• Advanced analytics\n\n"
            "💰 **Premium Plans:**\n"
            "• 7 days: 1000 kyat\n"
            "• 30 days: 3500 kyat\n"
            "• 90 days: 9000 kyat\n\n"
            "🎁 **3-day FREE trial available!**\n\n"
            "📞 **Contact admin to upgrade:**\n"
            "@When_the_night_falls_my_soul_se"
        )

def register_handlers(application: Application):
    """Register advanced start command handlers"""
    logger.info("Registering ADVANCED start handlers")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_start_callbacks, pattern="^(check_subscription|balance|detailed_stats|advanced_leaderboard|daily_challenges|premium_features|referral_center|achievements|withdrawal_menu|lb_|back_to_start)"))
