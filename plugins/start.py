from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import logging
import sys
import os
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import CURRENCY, MIN_WITHDRAWAL, MAX_DAILY_WITHDRAWAL, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Updated start image URL
START_IMAGE_URL = "https://i.ibb.co/DDbgt0JC/x.jpg"

# Conversation states for start menu withdrawal
START_WD_METHOD, START_WD_AMOUNT, START_WD_DETAILS = range(3)

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
        return True, []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced start command with image and custom design"""
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Start command by user {user_id} in chat {chat_id}")

    # Check for referral
    referred_by = None
    if context.args:
        try:
            ref_code = str(context.args[0])
            if ref_code.startswith("ref_"):
                referred_by = ref_code[4:]
            else:
                referred_by = ref_code
            logger.info(f"User {user_id} started with referral from {referred_by}")
        except Exception as e:
            logger.error(f"Error parsing referral ID for user {user_id}: {e}")

    # Check force subscription
    subscribed, not_subscribed_channels = await check_subscription(context, int(user_id), chat_id)
    if not subscribed:
        keyboard = []
        for i in range(0, len(not_subscribed_channels), 2):
            row = []
            channel_1 = not_subscribed_channels[i]
            row.append(InlineKeyboardButton(
                channel_1["channel_name"],
                url=f"https://t.me/{channel_1['channel_name'][1:]}"
            ))
            if i + 1 < len(not_subscribed_channels):
                channel_2 = not_subscribed_channels[i + 1]
                row.append(InlineKeyboardButton(
                    channel_2["channel_name"],
                    url=f"https://t.me/{channel_2['channel_name'][1:]}"
                ))
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Please join the following channels to use the bot:\n"
            "ကျေးဇူးပြု၍ အောက်ပါချန်နယ်များသို့ဝင်ရောက်ပါ။",
            reply_markup=reply_markup
        )
        logger.info(f"User {user_id} not subscribed to required channels: {[ch['channel_name'] for ch in not_subscribed_channels]}")
        return

    # Get or create user
    user = await db.get_user(user_id)
    is_new_user = False
    
    if not user:
        is_new_user = True
        user = await db.create_user(user_id, {
            "first_name": update.effective_user.first_name,
            "last_name": update.effective_user.last_name
        }, referred_by)
        if not user:
            logger.error(f"Failed to create user {user_id}")
            await update.message.reply_text("Error creating user. Please try again later.")
            return
        logger.info(f"Created new user {user_id} during start command")

        # Process referral bonus
        if referred_by:
            referrer = await db.get_user(referred_by)
            if referrer:
                referral_reward = await db.get_referral_reward()
                current_balance = referrer.get("balance", 0)
                new_invites = referrer.get("invites", 0) + 1
                successful_referrals = referrer.get("successful_referrals", 0) + 1
                
                await db.update_user(referred_by, {
                    "balance": current_balance + referral_reward,
                    "invites": new_invites,
                    "successful_referrals": successful_referrals
                })
                
                try:
                    await context.bot.send_message(
                        chat_id=referred_by,
                        text=f"🎉 **Your referral link worked!**\n\n"
                             f"👤 **{update.effective_user.first_name}** joined using your link!\n"
                             f"💰 **You earned:** {referral_reward} {CURRENCY}\n"
                             f"💵 **New Balance:** {int(current_balance + referral_reward)} {CURRENCY}\n"
                             f"🎯 **Keep sharing to earn more!**"
                    )
                    logger.info(f"Awarded {referral_reward} {CURRENCY} to referrer {referred_by} for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to notify referrer {referred_by}: {e}")

        # ANNOUNCE NEW USER
        try:
            from plugins.announcements import announcement_system
            await announcement_system.announce_new_user(
                user_id=user_id,
                user_name=update.effective_user.first_name or "New User",
                referred_by=referred_by,
                context=context
            )
        except Exception as e:
            logger.error(f"Failed to announce new user: {e}")

    # Get user stats
    current_balance = user.get("balance", 0)
    total_messages = user.get("messages", 0)
    user_level = user.get("user_level", 1)
    total_earnings = user.get("total_earnings", 0)
    successful_referrals = user.get("successful_referrals", 0)

    # Create welcome message with your custom format
    welcome_message = (
        f"စာပို့ရင်း ငွေရှာမယ်:\n"
        f"Welcome back, {update.effective_user.first_name}! 🎉\n\n"
        f"💰 Balance: {int(current_balance)} {CURRENCY}\n"
        f"📝 Messages: {total_messages}\n"
        f"🎯 Level: {user_level}\n"
        f"💸 Total Earned: {int(total_earnings)} {CURRENCY}\n"
        f"👥 Referrals: {successful_referrals}\n\n"
    )

    # Add top 5 users leaderboard as requested - FIXED
    try:
        users = await db.get_all_users()
        if users:
            # Sort by total earnings (as shown in your example)
            sorted_users = sorted(users, key=lambda x: x.get("total_earnings", 0), reverse=True)[:5]
            
            if sorted_users:
                for i, top_user in enumerate(sorted_users, 1):
                    # FIXED: Handle None values properly
                    name = top_user.get('first_name') or 'Unknown'
                    last_name = top_user.get('last_name') or ''
                    
                    # Only concatenate if last_name is not empty
                    if last_name:
                        full_name = f"{name} {last_name}".strip()
                    else:
                        full_name = name.strip()
                    
                    messages = top_user.get('messages', 0)
                    earnings = int(top_user.get('total_earnings', 0))
                    
                    welcome_message += f"{i}. {full_name} - {messages} msg, {earnings} {CURRENCY}\n"
                
    except Exception as e:
        logger.error(f"Error generating leaderboard: {e}")

    # Add referral sharing link to welcome message
    bot_username = context.bot.username or "ACTearnbot"
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    share_text = "💰%20Join%20this%20earning%20bot%20and%20make%20money%20by%20chatting!%20🚀"
    share_url = f"https://telegram.me/share/url?url={referral_link}&text={share_text}"
    
    welcome_message += f"\nဒီလင့်ကိုပို့ပြီး ငွေရှာလိုက်ပါ\n{share_url}\n"

    # Create custom keyboard with referral button
    keyboard = [
        [
            InlineKeyboardButton("Balance", callback_data="menu_balance"),
            InlineKeyboardButton("Withdraw", callback_data="menu_withdraw")
        ],
        [
            InlineKeyboardButton("ငွေထုတ်ချာနယ်", url="https://t.me/actearnproof"),
            InlineKeyboardButton("Join Group", url="https://t.me/+3Km76-24T3RjNzY1")
        ],
        [
            InlineKeyboardButton("လူခေါ်ရင်းငွေရှာ", callback_data="menu_referral")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        # Send the image first
        await update.message.reply_photo(
            photo=START_IMAGE_URL,
            caption=welcome_message,
            reply_markup=reply_markup
        )
        logger.info(f"Sent welcome message with image to user {user_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send image, sending text only: {e}")
        # Fallback to text-only message if image fails
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def handle_menu_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle balance button from start menu"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    
    await query.answer()
    logger.info(f"Balance button clicked by user {user_id}")
    
    try:
        user = await db.get_user(user_id)
        if user:
            balance = user.get("balance", 0)
            total_earned = user.get("total_earnings", 0)
            total_withdrawn = user.get("total_withdrawn", 0)
            messages = user.get("messages", 0)
            
            # Check for pending withdrawals
            pending_withdrawals = user.get("pending_withdrawals", [])
            pending_count = sum(1 for w in pending_withdrawals if w.get("status") == "PENDING")
            
            balance_text = (
                f"💰 **Your Balance**\n\n"
                f"💳 **Current Balance:** {int(balance)} {CURRENCY}\n"
                f"📈 **Total Earned:** {int(total_earned)} {CURRENCY}\n"
                f"💸 **Total Withdrawn:** {int(total_withdrawn)} {CURRENCY}\n"
                f"📝 **Total Messages:** {messages:,}\n"
                f"⏳ **Pending Withdrawals:** {pending_count}\n\n"
                f"သင့်လက်ကျန်ငွေသည် {int(balance)} ကျပ်ဖြစ်ပါသည်။\n\n"
                f"💡 Keep chatting in groups to earn more!\n"
                f"📊 Rate: 3 messages = 1 {CURRENCY}\n"
                f"📋 Use `/pending` to check withdrawal history"
            )
            
            await query.message.reply_text(balance_text)
        else:
            await query.message.reply_text("❌ User not found. Please try /start")
    except Exception as e:
        logger.error(f"Error in handle_menu_balance: {e}")
        await query.message.reply_text("❌ Error occurred. Please try /start again.")

async def handle_menu_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle referral button from start menu"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    
    await query.answer()
    logger.info(f"Referral button clicked by user {user_id}")
    
    try:
        user = await db.get_user(user_id)
        if user:
            bot_username = context.bot.username
            referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
            
            # Easy share URL
            share_text = "💰 Join this earning bot and make money by chatting! 🚀"
            share_url = f"https://telegram.me/share/url?url={referral_link}&text={share_text}"
            
            successful_referrals = user.get("successful_referrals", 0)
            total_invites = user.get("invites", 0)
            
            referral_reward = await db.get_referral_reward()
            
            referral_text = (
                f"👥 **Invite Friends & Earn!**\n\n"
                f"🔗 **Your Referral Link:**\n"
                f"`{referral_link}`\n\n"
                f"💰 **Earn {referral_reward} {CURRENCY} for each friend who:**\n"
                f"• Clicks your link\n"
                f"• Starts using the bot\n"
                f"• Sends their first message\n\n"
                f"📊 **Your Referral Stats:**\n"
                f"• Successful Referrals: {successful_referrals}\n"
                f"• Total Invites: {total_invites}\n\n"
                f"💡 **Tips:**\n"
                f"• Share in groups and social media\n"
                f"• Explain how the bot works\n"
                f"• Help friends get started\n\n"
                f"Start sharing and earn more! 🚀"
            )
            
            # Add easy share button
            share_keyboard = [
                [InlineKeyboardButton("📤 Easy Share", url=share_url)]
            ]
            share_markup = InlineKeyboardMarkup(share_keyboard)
            
            await query.message.reply_text(referral_text, reply_markup=share_markup)
        else:
            await query.message.reply_text("❌ User not found. Please try /start")
    except Exception as e:
        logger.error(f"Error in handle_menu_referral: {e}")
        await query.message.reply_text("❌ Error occurred. Please try /start again.")

async def handle_menu_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle withdraw button from start menu - FIXED - Send NEW message"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    
    await query.answer()
    logger.info(f"Withdraw button clicked by user {user_id}")
    
    try:
        user = await db.get_user(user_id)
        if not user:
            await query.message.reply_text("❌ User not found. Please try /start first")
            return ConversationHandler.END
        
        # Check for pending withdrawals first
        pending_withdrawals = user.get("pending_withdrawals", [])
        pending_count = sum(1 for w in pending_withdrawals if w.get("status") == "PENDING")
        
        if pending_count > 0:
            await query.message.reply_text(
                f"⏳ **You have {pending_count} pending withdrawal request(s)**\n\n"
                f"Please wait for admin approval or rejection before making a new request.\n\n"
                f"📋 Use `/pending` to check status\n"
                f"📞 Support: @When_the_night_falls_my_soul_se"
            )
            return ConversationHandler.END
        
        # Check minimum message requirement BUT SKIP FOR ADMIN/OWNER
        is_admin_or_owner = user_id in ADMIN_IDS
        messages_count = user.get("messages", 0)
        
        if not is_admin_or_owner and messages_count < 50:
            await query.message.reply_text(
                f"📝 **You need at least 50 messages to withdraw**\n\n"
                f"**Current:** {messages_count} messages\n"
                f"**Required:** 50 messages\n\n"
                f"ကျေးဇူးပြု၍ အနည်းဆုံး ၅၀ စာ ပို့ပြီးမှ ငွေထုတ်ပါ။\n\n"
                f"💡 Chat in groups to earn messages!"
            )
            return ConversationHandler.END
        
        # Check if user is banned
        if user.get("banned", False):
            await query.message.reply_text(
                f"🚫 **You are banned from using this bot**\n\n"
                f"သင်သည် ဤဘော့ကို အသုံးပြုခွင့် ပိတ်ပင်ထားပါသည်။\n\n"
                f"📞 Contact support: @When_the_night_falls_my_soul_se"
            )
            return ConversationHandler.END
        
        # All checks passed - show withdrawal options
        current_balance = user.get("balance", 0)
        
        # Create payment method selection keyboard with UNIQUE prefixes
        keyboard = [
            [
                InlineKeyboardButton("💳 KBZ Pay", callback_data="startwd_method_KBZ Pay"),
                InlineKeyboardButton("🌊 Wave Pay", callback_data="startwd_method_Wave Pay")
            ],
            [
                InlineKeyboardButton("₿ Binance Pay", callback_data="startwd_method_Binance Pay"),
                InlineKeyboardButton("📱 Phone Bill", callback_data="startwd_method_Phone Bill")
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data="startwd_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Special message for admin/owner
        admin_note = f"\n👑 **ADMIN ACCESS** - Message requirement bypassed!" if is_admin_or_owner else ""
        
        prompt_msg = (
            f"💸 **WITHDRAWAL REQUEST**\n\n"
            f"💰 **Current Balance:** {int(current_balance)} {CURRENCY}\n"
            f"💎 **Minimum:** {MIN_WITHDRAWAL} {CURRENCY}\n"
            f"📈 **Daily Limit:** {MAX_DAILY_WITHDRAWAL:,} {CURRENCY}{admin_note}\n\n"
            f"⚠️ **Note:** Amount will be deducted when you submit request\n"
            f"🔄 **Refunded if rejected by admin**\n\n"
            f"🏦 **ကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ:**\n"
            f"Please select your payment method:"
        )
        
        # Clear any existing user data
        context.user_data.clear()
        
        # FIXED: Send NEW message instead of editing photo caption
        withdrawal_msg = await query.message.reply_text(prompt_msg, reply_markup=reply_markup)
        
        # Store the message ID for later editing
        context.user_data["withdrawal_message_id"] = withdrawal_msg.message_id
        
        logger.info(f"Start menu withdrawal initiated by user {user_id} (Admin: {is_admin_or_owner})")
        
        return START_WD_METHOD
        
    except Exception as e:
        logger.error(f"Error in handle_menu_withdraw: {e}")
        await query.message.reply_text(
            f"❌ Error occurred.\n\n"
            f"💡 **Try:** `/withdraw`"
        )
        return ConversationHandler.END

async def handle_start_wd_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle payment method selection from start menu"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    logger.info(f"Start withdrawal method selection: {data} by user {user_id}")

    try:
        await query.answer()

        if data == "startwd_cancel":
            await query.edit_message_text(
                "❌ **Withdrawal Cancelled**\n\n"
                "ငွေထုတ်မှု လုပ်ငန်းစဉ်ကို ပယ်ဖျက်လိုက်ပါပြီ။\n"
                "Use the Withdraw button or /withdraw to start again."
            )
            return ConversationHandler.END

        # Handle withdrawal method callbacks specifically
        if not data.startswith("startwd_method_"):
            await query.edit_message_text("❌ Invalid selection. Please try again.")
            return ConversationHandler.END

        method = data.replace("startwd_method_", "")
        payment_methods = ["KBZ Pay", "Wave Pay", "Binance Pay", "Phone Bill"]
        
        if method not in payment_methods:
            await query.edit_message_text("❌ Invalid payment method. Please try again.")
            return START_WD_METHOD

        context.user_data["payment_method"] = method
        logger.info(f"User {user_id} selected payment method: {method}")

        # Special handling for Phone Bill (fixed amount)
        if method == "Phone Bill":
            context.user_data["withdrawal_amount"] = 1000
            await query.edit_message_text(
                f"📱 **Phone Bill Withdrawal**\n\n"
                f"💰 **Fixed Amount:** 1000 {CURRENCY}\n\n"
                f"⚠️ **Amount will be deducted from your balance when you submit**\n\n"
                f"📞 **သင့်ဖုန်းနံပါတ်ကို ထည့်ပါ:**\n"
                f"Please enter your phone number (e.g., 09123456789):"
            )
            return START_WD_DETAILS

        # For other methods, ask for amount
        user = await db.get_user(user_id)
        current_balance = user.get("balance", 0) if user else 0
        
        await query.edit_message_text(
            f"💰 **Enter Withdrawal Amount**\n\n"
            f"🏦 **Payment Method:** {method}\n"
            f"💳 **Your Balance:** {int(current_balance)} {CURRENCY}\n"
            f"💎 **Minimum:** {MIN_WITHDRAWAL} {CURRENCY}\n"
            f"📈 **Maximum Today:** {MAX_DAILY_WITHDRAWAL:,} {CURRENCY}\n\n"
            f"⚠️ **Important:** Amount will be deducted when you submit\n"
            f"🔄 **Refunded if admin rejects your request**\n\n"
            f"💸 **ငွေထုတ်ရန် ပမာဏကို ထည့်ပါ:**\n"
            f"Please enter the amount to withdraw:"
        )
        return START_WD_AMOUNT

    except Exception as e:
        logger.error(f"Error in handle_start_wd_method: {e}")
        await query.edit_message_text("❌ Error occurred. Please try /withdraw.")
        return ConversationHandler.END

async def handle_start_wd_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle withdrawal amount input from start menu"""
    user_id = str(update.effective_user.id)
    message = update.message
    logger.info(f"Start withdrawal amount input: {message.text} by user {user_id}")

    try:
        payment_method = context.user_data.get("payment_method")
        if not payment_method:
            await message.reply_text("❌ Session expired. Please try /withdraw")
            return ConversationHandler.END

        # Parse and validate amount
        try:
            amount = int(float(message.text.strip()))
        except ValueError:
            await message.reply_text(
                "❌ **Invalid Amount**\n\n"
                "ကျေးဇူးပြု၍ မှန်ကန်သော နံပါတ်ထည့်ပါ (e.g., 1000)\n"
                "Please enter a valid number."
            )
            return START_WD_AMOUNT

        # Validate minimum amount
        if amount < MIN_WITHDRAWAL:
            await message.reply_text(
                f"❌ **Amount Too Low**\n\n"
                f"အနည်းဆုံး ငွေထုတ်ပမာဏ: {MIN_WITHDRAWAL} {CURRENCY}\n"
                f"Minimum withdrawal: {MIN_WITHDRAWAL} {CURRENCY}"
            )
            return START_WD_AMOUNT

        # Validate maximum daily limit
        if amount > MAX_DAILY_WITHDRAWAL:
            await message.reply_text(
                f"❌ **Amount Too High**\n\n"
                f"နေ့စဉ် အများဆုံး: {MAX_DAILY_WITHDRAWAL:,} {CURRENCY}\n"
                f"Daily maximum: {MAX_DAILY_WITHDRAWAL:,} {CURRENCY}"
            )
            return START_WD_AMOUNT

        # Check user balance
        user = await db.get_user(user_id)
        if not user:
            await message.reply_text("❌ User not found. Please restart with /start")
            return ConversationHandler.END

        balance = user.get("balance", 0)
        if balance < amount:
            await message.reply_text(
                f"❌ **Insufficient Balance**\n\n"
                f"💰 Your Balance: {int(balance)} {CURRENCY}\n"
                f"💸 Requested: {amount} {CURRENCY}\n"
                f"💡 Need {amount - int(balance)} more {CURRENCY}\n\n"
                f"လက်ကျန်ငွေ မလုံလောက်ပါ။"
            )
            return START_WD_AMOUNT

        context.user_data["withdrawal_amount"] = amount

        # Prompt for payment details based on method
        if payment_method == "KBZ Pay":
            detail_prompt = (
                f"🏦 **KBZ Pay Details Required**\n\n"
                f"💰 Amount: {amount} {CURRENCY}\n"
                f"💳 Method: {payment_method}\n\n"
                f"⚠️ **Amount will be deducted when you submit**\n\n"
                f"📱 **Please provide:**\n"
                f"• Phone number (09XXXXXXXX)\n"
                f"• Account holder name\n"
                f"• OR send QR code image\n\n"
                f"ဥပမာ: 09123456789 Mg Mg"
            )
        elif payment_method == "Wave Pay":
            detail_prompt = (
                f"🌊 **Wave Pay Details Required**\n\n"
                f"💰 Amount: {amount} {CURRENCY}\n"
                f"💳 Method: {payment_method}\n\n"
                f"⚠️ **Amount will be deducted when you submit**\n\n"
                f"📱 **Please provide:**\n"
                f"• Phone number (09XXXXXXXX)\n"
                f"• Account holder name\n"
                f"• OR send QR code image\n\n"
                f"ဥပမာ: 09123456789 Ma Ma"
            )
        elif payment_method == "Binance Pay":
            detail_prompt = (
                f"₿ **Binance Pay Details Required**\n\n"
                f"💰 Amount: {amount} {CURRENCY}\n"
                f"💳 Method: {payment_method}\n\n"
                f"⚠️ **Amount will be deducted when you submit**\n\n"
                f"📱 **Please provide:**\n"
                f"• Binance Pay ID or Email\n"
                f"• Account holder name\n"
                f"• OR send QR code image\n\n"
                f"ဥပမာ: your@email.com or Binance ID"
            )

        await message.reply_text(detail_prompt)
        return START_WD_DETAILS

    except Exception as e:
        logger.error(f"Error in handle_start_wd_amount: {e}")
        await message.reply_text("❌ Error occurred. Please try /withdraw")
        return ConversationHandler.END

async def handle_start_wd_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle withdrawal details from start menu - COMPLETE PROCESSING"""
    user_id = str(update.effective_user.id)
    logger.info(f"Start withdrawal details from user {user_id}")

    try:
        amount = context.user_data.get("withdrawal_amount")
        payment_method = context.user_data.get("payment_method")
        
        if not amount or not payment_method:
            await update.message.reply_text("❌ Session expired. Please restart")
            return ConversationHandler.END

        # Import and use the main withdrawal details handler
        from plugins.withdrawal import handle_details as main_handle_details
        
        # Call the main withdrawal details handler to complete the process
        result = await main_handle_details(update, context)
        
        # Return the result from the main handler
        return result

    except Exception as e:
        logger.error(f"Error in handle_start_wd_details: {e}")
        await update.message.reply_text("❌ Error occurred. Please try /withdraw")
        return ConversationHandler.END

def register_handlers(application: Application):
    """Register start command handlers with INDEPENDENT withdrawal conversation"""
    logger.info("Registering ENHANCED start handlers with INDEPENDENT WITHDRAWAL")
    
    # Register start command
    application.add_handler(CommandHandler("start", start))
    
    # Register balance button handler (simple callback)
    application.add_handler(CallbackQueryHandler(
        handle_menu_balance, 
        pattern="^menu_balance$"
    ))
    
    # Register referral button handler
    application.add_handler(CallbackQueryHandler(
        handle_menu_referral, 
        pattern="^menu_referral$"
    ))
    
    # Create SEPARATE conversation handler for start menu withdrawals
    start_withdrawal_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_menu_withdraw, pattern="^menu_withdraw$")
        ],
        states={
            START_WD_METHOD: [
                # FIXED: More specific pattern matching
                CallbackQueryHandler(handle_start_wd_method, pattern="^startwd_method_KBZ Pay$"),
                CallbackQueryHandler(handle_start_wd_method, pattern="^startwd_method_Wave Pay$"),
                CallbackQueryHandler(handle_start_wd_method, pattern="^startwd_method_Binance Pay$"),
                CallbackQueryHandler(handle_start_wd_method, pattern="^startwd_method_Phone Bill$"),
                CallbackQueryHandler(handle_start_wd_method, pattern="^startwd_cancel$")
            ],
            START_WD_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_start_wd_amount)
            ],
            START_WD_DETAILS: [
                MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_start_wd_details)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(handle_start_wd_method, pattern="^startwd_cancel$")
        ],
        allow_reentry=True,
        name="start_withdrawal_conversation",
        persistent=False
    )
    
    # Register the start withdrawal conversation
    application.add_handler(start_withdrawal_conv)
    
    logger.info("✅ ENHANCED start handlers with INDEPENDENT WITHDRAWAL registered successfully")
