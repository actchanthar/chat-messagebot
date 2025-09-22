from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import logging
import sys
import os
import re

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import CURRENCY, BOT_NAME, APPROVED_GROUPS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command with referral system and channel requirements"""
    user_id = str(update.effective_user.id)
    user = update.effective_user
    logger.info(f"Start command from user {user_id}")

    try:
        # Extract referral code from command arguments
        referred_by = None
        if context.args:
            ref_arg = context.args[0]
            if ref_arg.startswith("ref_"):
                referred_by = ref_arg[4:]  # Remove "ref_" prefix
                logger.info(f"User {user_id} referred by {referred_by}")

        # Check if user already exists
        existing_user = await db.get_user(user_id)
        
        if existing_user:
            # Existing user - show welcome back message
            current_balance = existing_user.get("balance", 0)
            total_earnings = existing_user.get("total_earnings", 0)
            messages_count = existing_user.get("messages", 0)
            referrals = existing_user.get("successful_referrals", 0)
            
            welcome_text = (
                f"👋 **ကြိုဆိုပါတယ် {user.first_name}!**\n\n"
                f"💰 **လက်ကျန်ငွေ:** {int(current_balance)} {CURRENCY}\n"
                f"📈 **စုစုပေါင်းရငွေ:** {int(total_earnings)} {CURRENCY}\n"
                f"💬 **ပို့ထားသောစာ:** {messages_count:,} စာ\n"
                f"👥 **ဖိတ်ကြားမှုများ:** {referrals} မိတ်ဆွေ\n\n"
                f"🎯 **ငွေရှာနည်း:**\n"
                f"• Approved Groups များထဲမှာ စာပို့ပါ\n"
                f"• ၃ စာ ပို့တိုင်း ၁ {CURRENCY} ရပါမယ်\n"
                f"• အနည်းဆုံး ၂၀၀ {CURRENCY} ငွေထုတ်နိုင်ပါတယ်\n\n"
                f"🔗 **မိတ်ဆွေများကို ဖိတ်ကြားပြီး ၅၀ {CURRENCY} ရယူပါ!**\n"
                f"**သင့်ရဲ့ ဖိတ်ကြားလင့်:** `https://t.me/{context.bot.username}?start=ref_{user_id}`"
            )
            
            # Create main menu keyboard
            keyboard = [
                [
                    InlineKeyboardButton("💰 ငွေထုတ်မယ်", callback_data="withdraw_menu"),
                    InlineKeyboardButton("📊 ကျွန်တော့်အခြေအနေ", callback_data="my_profile")
                ],
                [
                    InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard_menu"),
                    InlineKeyboardButton("👥 မိတ်ဆွေဖိတ်မယ်", callback_data="invite_friends")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
        else:
            # New user - create account
            user_data = {
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "username": user.username or ""
            }
            
            new_user = await db.create_user(user_id, user_data, referred_by)
            
            if not new_user:
                await update.message.reply_text("❌ အကောင့်ဖွင့်၍မရပါ။ ထပ်မံကြိုးစားပါ။")
                return
            
            # Welcome message for new user
            welcome_text = (
                f"🎉 **{BOT_NAME} မှ ကြိုဆိုပါတယ်!**\n\n"
                f"👤 **{user.first_name}**, သင့်အကောင့်ကို အောင်မြင်စွာ ဖွင့်လှစ်ပါပြီ!\n\n"
                f"🎁 **Welcome Bonus:** ၁၀၀ {CURRENCY} ရရှိပါပြီ!\n\n"
                f"💡 **ငွေရှာနည်း:**\n"
                f"• Approved Groups များတွင် စာများပို့ပါ\n"
                f"• ၃ စာ ပို့တိုင်း ၁ {CURRENCY} ရပါမယ်\n"
                f"• မိတ်ဆွေများကို ဖိတ်ကြားပြီး ၅၀ {CURRENCY} ရပါ\n"
                f"• အနည်းဆုံး ၂၀၀ {CURRENCY} ငွေထုတ်နိုင်ပါတယ်\n\n"
                f"📋 **လိုအပ်ချက်များ:**\n"
                f"• Mandatory channels များ join လုပ်ရပါမယ်\n"
                f"• အနည်းဆုံး ၁၀ မိတ်ဆွေ ဖိတ်ကြားရပါမယ်\n"
                f"• အနည်းဆုံး ၅၀ စာ ပို့ရပါမယ်\n\n"
            )
            
            # Check if this is a referral and there are mandatory channels
            channels = await db.get_mandatory_channels()
            
            if referred_by and channels:
                # Special handling for referred users
                keyboard = []
                
                # Add join buttons for each channel
                for channel in channels[:5]:  # Show max 5 channels
                    channel_name = channel.get('channel_name', 'Channel')
                    channel_id = channel.get('channel_id')
                    
                    try:
                        # Try to get proper invite link
                        chat_info = await context.bot.get_chat(channel_id)
                        if hasattr(chat_info, 'invite_link') and chat_info.invite_link:
                            join_url = chat_info.invite_link
                        elif hasattr(chat_info, 'username') and chat_info.username:
                            join_url = f"https://t.me/{chat_info.username}"
                        else:
                            join_url = f"https://t.me/c/{channel_id.replace('-100', '')}"
                    except:
                        join_url = f"https://t.me/c/{channel_id.replace('-100', '')}"
                    
                    keyboard.append([InlineKeyboardButton(f"📺 Join {channel_name}", url=join_url)])
                
                # Add verification button
                keyboard.append([InlineKeyboardButton("✅ I Joined All Channels", callback_data="check_referral_channels")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Get referrer name
                referrer_name = "friend"
                try:
                    referrer_info = await context.bot.get_chat(int(referred_by))
                    referrer_name = referrer_info.first_name or "friend"
                except:
                    pass
                
                welcome_text += f"\n🎁 **SPECIAL REFERRAL BONUS**\n\n"
                welcome_text += f"👥 **You were invited by {referrer_name}!**\n"
                welcome_text += f"💰 **Join all channels below to activate referral bonus**\n"
                welcome_text += f"🎯 **Your friend will get 50 {CURRENCY} when you join all channels**\n\n"
                welcome_text += f"📺 **Please join these channels to continue:**"
                
            else:
                # Regular new user or no channels
                keyboard = [
                    [
                        InlineKeyboardButton("💰 Start Earning", callback_data="start_earning"),
                        InlineKeyboardButton("👥 Invite Friends", callback_data="invite_friends")
                    ],
                    [
                        InlineKeyboardButton("ℹ️ How to Earn", callback_data="how_to_earn"),
                        InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard_menu")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                welcome_text += f"🚀 **Ready to start earning? Click the buttons below!**"
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again later.")

async def handle_referral_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle referral channel check callback"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    
    await query.answer()
    
    try:
        # Check if user joined all channels
        from plugins.withdrawal import check_user_subscriptions
        requirements_met, joined, not_joined, referral_count = await check_user_subscriptions(user_id, context)
        
        if len(not_joined) == 0:
            # All channels joined
            await query.edit_message_text(
                "✅ **CONGRATULATIONS!**\n\n"
                "🎉 You joined all mandatory channels!\n"
                "💰 Your referrer will receive their bonus now!\n"
                "🚀 Start chatting in groups to earn kyat!\n\n"
                "💡 **How to earn:**\n"
                "• Send messages in approved groups\n"
                "• Earn 1 kyat every 3 messages\n"
                "• Invite more friends for bonuses!\n\n"
                f"**Your referral link:**\n"
                f"`https://t.me/{context.bot.username}?start=ref_{user_id}`"
            )
            
            # Process referral reward
            await db.check_and_process_referral_reward(user_id, context)
            
        else:
            # Not all channels joined
            not_joined_names = [ch['name'] for ch in not_joined[:3]]
            await query.edit_message_text(
                f"❌ **Please join ALL channels first**\n\n"
                f"✅ **Joined:** {len(joined)} channels\n"
                f"❌ **Still need to join:** {len(not_joined)} channels\n\n"
                f"**Missing channels:** {', '.join(not_joined_names)}\n\n"
                f"💡 **Join all channels then click the button again**"
            )
        
    except Exception as e:
        logger.error(f"Error in referral check: {e}")
        await query.edit_message_text("❌ Error checking channels. Please try again.")

async def handle_start_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle start menu callbacks"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    await query.answer()
    
    try:
        if data == "withdraw_menu":
            await query.edit_message_text(
                "💰 **WITHDRAWAL MENU**\n\n"
                "To start withdrawal, use the command:\n"
                "👉 `/withdraw`\n\n"
                "**Requirements:**\n"
                "• Join all mandatory channels\n"
                "• Invite at least 10 friends\n"
                "• Send at least 50 messages\n"
                "• Minimum 200 kyat balance\n\n"
                "**Payment Methods:**\n"
                "• KBZ Pay\n"
                "• Wave Pay\n"
                "• Binance Pay\n"
                "• Phone Bill Top-up"
            )
            
        elif data == "my_profile":
            user = await db.get_user(user_id)
            if user:
                balance = user.get("balance", 0)
                earnings = user.get("total_earnings", 0)
                messages = user.get("messages", 0)
                referrals = user.get("successful_referrals", 0)
                withdrawn = user.get("total_withdrawn", 0)
                
                # Get user rank
                rank = await db.get_user_rank_by_earnings(user_id)
                total_users = await db.get_total_users_count()
                
                profile_text = (
                    f"👤 **YOUR PROFILE**\n\n"
                    f"💰 **Balance:** {int(balance)} {CURRENCY}\n"
                    f"📈 **Total Earned:** {int(earnings)} {CURRENCY}\n"
                    f"💸 **Total Withdrawn:** {int(withdrawn)} {CURRENCY}\n"
                    f"💬 **Messages Sent:** {messages:,}\n"
                    f"👥 **Successful Referrals:** {referrals}\n"
                    f"🏆 **Rank:** #{rank} of {total_users:,}\n\n"
                    f"🎯 **Keep chatting to earn more!**\n"
                    f"📋 **Referral Link:**\n"
                    f"`https://t.me/{context.bot.username}?start=ref_{user_id}`"
                )
                await query.edit_message_text(profile_text)
            
        elif data == "invite_friends":
            await query.edit_message_text(
                f"👥 **INVITE FRIENDS & EARN!**\n\n"
                f"💰 **Earn 50 {CURRENCY} for each friend who:**\n"
                f"• Joins using your link\n"
                f"• Joins all mandatory channels\n"
                f"• Stays active in the community\n\n"
                f"🔗 **Your Referral Link:**\n"
                f"`https://t.me/{context.bot.username}?start=ref_{user_id}`\n\n"
                f"📤 **How to share:**\n"
                f"1. Copy the link above\n"
                f"2. Share with friends on social media\n"
                f"3. Explain they'll get 100 {CURRENCY} welcome bonus\n"
                f"4. You get 50 {CURRENCY} when they join channels\n\n"
                f"🎯 **No limit on referrals - invite unlimited friends!**"
            )
            
        elif data == "leaderboard_menu":
            await query.edit_message_text(
                "🏆 **LEADERBOARD & RANKINGS**\n\n"
                "View rankings with command:\n"
                "👉 `/leaderboard` or `/lb`\n\n"
                "**Categories:**\n"
                "• 💰 Top Earners\n"
                "• 💬 Most Active Users\n"
                "• 💳 Richest Users\n"
                "• 💸 Top Withdrawers\n"
                "• 👥 Best Referrers\n\n"
                "Check your personal rank:\n"
                "👉 `/rank` or `/myrank`"
            )
            
        elif data == "start_earning":
            # Get approved groups list
            group_info = []
            for group_id in APPROVED_GROUPS:
                try:
                    chat = await context.bot.get_chat(group_id)
                    if hasattr(chat, 'username') and chat.username:
                        group_info.append(f"• @{chat.username}")
                    else:
                        group_info.append(f"• {chat.title or 'Group'}")
                except:
                    group_info.append(f"• Group {group_id}")
            
            groups_text = '\n'.join(group_info[:5]) if group_info else "• Check bot announcements for group links"
            
            await query.edit_message_text(
                f"🚀 **START EARNING NOW!**\n\n"
                f"💰 **How it works:**\n"
                f"1. Join approved groups below\n"
                f"2. Send messages in those groups\n"
                f"3. Earn 1 {CURRENCY} every 3 messages\n"
                f"4. Withdraw when you reach 200 {CURRENCY}\n\n"
                f"📺 **Approved Groups:**\n"
                f"{groups_text}\n\n"
                f"⚠️ **Important:**\n"
                f"• Only meaningful messages count\n"
                f"• No spam or repeated messages\n"
                f"• Join mandatory channels to withdraw\n\n"
                f"🎯 **Start chatting and earning now!**"
            )
            
        elif data == "how_to_earn":
            await query.edit_message_text(
                f"💡 **HOW TO EARN {CURRENCY}**\n\n"
                f"**1. Chat in Groups (Primary Method):**\n"
                f"• Send messages in approved groups\n"
                f"• Earn 1 {CURRENCY} every 3 messages\n"
                f"• Only meaningful messages count\n\n"
                f"**2. Referral System:**\n"
                f"• Invite friends = 50 {CURRENCY} each\n"
                f"• Friends must join mandatory channels\n"
                f"• Unlimited referrals allowed\n\n"
                f"**3. Milestones & Bonuses:**\n"
                f"• Special rewards at major milestones\n"
                f"• Bonus events and competitions\n"
                f"• Active user rewards\n\n"
                f"**Withdrawal Requirements:**\n"
                f"• Minimum 200 {CURRENCY}\n"
                f"• Join all mandatory channels\n"
                f"• 10+ successful referrals\n"
                f"• 50+ messages sent\n\n"
                f"🎯 **Start earning today!**"
            )
    
    except Exception as e:
        logger.error(f"Error in start callbacks: {e}")
        await query.edit_message_text("❌ Error occurred. Please try again.")

def register_handlers(application: Application):
    """Register start command handlers"""
    logger.info("Registering start handlers with advanced referral system")
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(handle_referral_check, pattern="^check_referral_channels$"))
    application.add_handler(CallbackQueryHandler(handle_start_callbacks, pattern="^(withdraw_menu|my_profile|invite_friends|leaderboard_menu|start_earning|how_to_earn)$"))
    
    logger.info("✅ Start handlers with advanced referral system registered successfully")
