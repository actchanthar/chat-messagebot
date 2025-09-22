from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)
from telegram.error import TelegramError, BadRequest
import logging
import sys
import os
from datetime import datetime, timezone
import traceback
import asyncio

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config import (
    MIN_WITHDRAWAL,
    MAX_DAILY_WITHDRAWAL,
    CURRENCY,
    LOG_CHANNEL_ID,
    ADMIN_IDS,
    APPROVED_GROUPS,
    RECEIPT_CHANNEL_ID,
    AUTO_ANNOUNCE_WITHDRAWALS,
    GENERAL_ANNOUNCEMENT_GROUPS
)
from database.database import db

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
STEP_PAYMENT_METHOD, STEP_AMOUNT, STEP_DETAILS = range(3)

# Updated payment methods as requested
PAYMENT_METHODS = ["KBZ Pay", "Wave Pay", "Binance Pay", "Phone Bill"]

async def get_next_order_id():
    """Get next sequential order ID"""
    try:
        # Get the highest order ID from database
        settings = await db.get_settings()
        current_order_id = settings.get("last_order_id", 0)
        
        # Increment for new order
        next_order_id = current_order_id + 1
        
        # Update in database
        await db.update_settings({"last_order_id": next_order_id})
        
        return next_order_id
    except Exception as e:
        logger.error(f"Error getting next order ID: {e}")
        # Fallback to timestamp-based ID
        return int(datetime.now().timestamp()) % 100000

async def check_user_subscriptions(user_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Check if user has joined all mandatory channels and invited enough users"""
    try:
        # Get mandatory channels
        channels = await db.get_mandatory_channels()
        
        joined_channels = []
        not_joined_channels = []
        
        # Check each channel
        for channel in channels:
            channel_id = channel.get('channel_id')
            channel_name = channel.get('channel_name', 'Unknown Channel')
            
            try:
                # Check if user is member of channel
                member = await context.bot.get_chat_member(channel_id, int(user_id))
                
                if member.status in ['member', 'administrator', 'creator']:
                    joined_channels.append({
                        'id': channel_id,
                        'name': channel_name,
                        'status': 'joined'
                    })
                else:
                    not_joined_channels.append({
                        'id': channel_id,
                        'name': channel_name,
                        'status': 'not_joined'
                    })
                    
            except TelegramError:
                # User is not a member or channel not accessible
                not_joined_channels.append({
                    'id': channel_id,
                    'name': channel_name,
                    'status': 'not_joined'
                })
        
        # Check referral count
        user = await db.get_user(user_id)
        referral_count = user.get('successful_referrals', 0) if user else 0
        
        # User must join all channels AND have 10+ referrals
        all_requirements_met = len(not_joined_channels) == 0 and referral_count >= 10
        
        return all_requirements_met, joined_channels, not_joined_channels, referral_count
        
    except Exception as e:
        logger.error(f"Error checking subscriptions for {user_id}: {e}")
        return False, [], [], 0

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the /withdraw command to initiate withdrawal process."""
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Withdraw command initiated by user {user_id}")

    try:
        # Check if command is used in private chat
        if update.effective_chat.type != "private":
            error_msg = "🔒 ကျေးဇူးပြု၍ /withdraw ကို သီးသန့်ချက်တွင်သာ အသုံးပြုပါ။\nFor security, please use withdrawal in private chat only."
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            logger.warning(f"User {user_id} attempted withdrawal in non-private chat")
            return ConversationHandler.END

        # Get user from database
        user = await db.get_user(user_id)
        if not user:
            error_msg = "❌ အသုံးပြုသူ မတွေ့ပါ။ ကျေးဇူးပြု၍ /start ဖြင့် စတင်ပါ။\nUser not found. Please start with /start."
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            return ConversationHandler.END

        # Check if user is banned
        if user.get("banned", False):
            error_msg = "🚫 သင်သည် ဤဘော့ကို အသုံးပြုခွင့် ပိတ်ပင်ထားပါသည်။\nYou are banned from using this bot."
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            return ConversationHandler.END

        # Check force join requirements FIRST
        try:
            requirements_met, joined, not_joined, referral_count = await check_user_subscriptions(user_id, context)
            
            if not requirements_met:
                # Create join buttons for not joined channels
                keyboard = []
                
                # Add join buttons for channels
                for channel in not_joined[:5]:  # Show max 5 channels
                    channel_name = channel['name']
                    channel_id = channel['id']
                    
                    # Create join button with proper URL
                    try:
                        # Get channel info to create proper invite link
                        chat_info = await context.bot.get_chat(channel_id)
                        if hasattr(chat_info, 'invite_link') and chat_info.invite_link:
                            join_url = chat_info.invite_link
                        else:
                            # Fallback to username-based link if available
                            if hasattr(chat_info, 'username') and chat_info.username:
                                join_url = f"https://t.me/{chat_info.username}"
                            else:
                                join_url = f"https://t.me/c/{channel_id.replace('-100', '')}"
                    except:
                        join_url = f"https://t.me/c/{channel_id.replace('-100', '')}"
                    
                    keyboard.append([InlineKeyboardButton(f"📺 Join {channel_name}", url=join_url)])
                
                # Add refresh button
                keyboard.append([InlineKeyboardButton("🔄 Check Requirements", callback_data="check_withdrawal_req")])
                
                # Add referral link button if needed
                if referral_count < 10:
                    keyboard.append([InlineKeyboardButton("👥 My Referral Link", callback_data="get_referral_link")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                requirements_text = (
                    f"🚫 **WITHDRAWAL REQUIREMENTS NOT MET**\n\n"
                    f"**ငွေထုတ်ရန် လိုအပ်ချက်များ:**\n\n"
                    f"📺 **Join Required Channels:** {len(joined)}/{len(joined) + len(not_joined)} {'✅' if len(not_joined) == 0 else '❌'}\n"
                    f"👥 **Invite Friends:** {referral_count}/10 {'✅' if referral_count >= 10 else '❌'}\n\n"
                )
                
                if not_joined:
                    requirements_text += f"**❌ You must join these channels:**\n"
                    for i, channel in enumerate(not_joined[:5], 1):
                        requirements_text += f"{i}. {channel['name']}\n"
                    requirements_text += f"\n"
                
                if referral_count < 10:
                    requirements_text += f"**❌ You need {10 - referral_count} more referrals**\n"
                    requirements_text += f"📤 **Your referral link:**\n"
                    requirements_text += f"`https://t.me/{context.bot.username}?start=ref_{user_id}`\n\n"
                
                requirements_text += f"💡 **Complete all requirements to enable withdrawal**\n"
                requirements_text += f"🎯 **Join channels and invite friends to proceed**"
                
                if update.callback_query:
                    await update.callback_query.answer()
                    await update.callback_query.message.edit_text(requirements_text, reply_markup=reply_markup)
                else:
                    await update.message.reply_text(requirements_text, reply_markup=reply_markup)
                
                return ConversationHandler.END
                
        except Exception as e:
            logger.error(f"Error checking force join requirements: {e}")
            # Continue if force join check fails

        # Check minimum message requirement BUT SKIP FOR ADMIN/OWNER
        is_admin_or_owner = user_id in ADMIN_IDS
        messages_count = user.get("messages", 0)
        
        if not is_admin_or_owner and messages_count < 50:
            error_msg = f"📝 You need at least 50 messages to withdraw. Current: {messages_count} messages.\nကျေးဇူးပြု၍ အနည်းဆုံး ၅၀ စာ ပို့ပြီးမှ ငွေထုတ်ပါ။"
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            return ConversationHandler.END

        # Check for pending withdrawals
        pending_withdrawals = user.get("pending_withdrawals", [])
        pending_count = sum(1 for w in pending_withdrawals if w.get("status") == "PENDING")
        if pending_count > 0:
            error_msg = (
                "⏳ သင့်တွင် ဆိုင်းငံ့ထားသော ငွေထုတ်မှု ရှိနေပါသည်။\n"
                "Admin မှ အတည်ပြုပြီးမှ သို့မဟုတ် ငြင်းပယ်ပြီးမှ နောက်ထပ် ငွေထုတ်နိုင်ပါသည်။\n\n"
                "You have pending withdrawal requests. Please wait for admin decision."
            )
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            return ConversationHandler.END

        # Clear user data for fresh withdrawal
        context.user_data.clear()

        # Create payment method selection keyboard (2 buttons per row as requested)
        keyboard = [
            [
                InlineKeyboardButton("💳 KBZ Pay", callback_data="wd_method_KBZ Pay"),
                InlineKeyboardButton("🌊 Wave Pay", callback_data="wd_method_Wave Pay")
            ],
            [
                InlineKeyboardButton("₿ Binance Pay", callback_data="wd_method_Binance Pay"),
                InlineKeyboardButton("📱 Phone Bill", callback_data="wd_method_Phone Bill")
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data="wd_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send payment method selection prompt
        current_balance = user.get("balance", 0)
        
        # Special message for admin/owner
        admin_note = f"\n👑 **ADMIN ACCESS** - All requirements bypassed!" if is_admin_or_owner else ""
        
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
        
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.edit_text(prompt_msg, reply_markup=reply_markup)
        else:
            await update.message.reply_text(prompt_msg, reply_markup=reply_markup)
        
        logger.info(f"Prompted user {user_id} for payment method selection (Admin: {is_admin_or_owner})")
        return STEP_PAYMENT_METHOD

    except Exception as e:
        logger.error(f"Error in withdraw for user {user_id}: {e}")
        error_msg = "❌ An unexpected error occurred. Please try again later."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
        return ConversationHandler.END

async def handle_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle payment method selection."""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    logger.info(f"Payment method selection for user {user_id}: {data}")

    try:
        await query.answer()

        if data == "wd_cancel":
            await query.edit_message_text(
                "❌ **Withdrawal Cancelled**\n\n"
                "ငွေထုတ်မှု လုပ်ငန်းစဉ်ကို ပယ်ဖျက်လိုက်ပါပြီ။\n"
                "Use /withdraw to start again anytime."
            )
            return ConversationHandler.END

        # Handle withdrawal requirement callbacks
        if data == "check_withdrawal_req":
            # Restart withdrawal process
            return await withdraw(update, context)
        
        if data == "get_referral_link":
            referral_link = f"https://t.me/{context.bot.username}?start=ref_{user_id}"
            await query.answer()
            await context.bot.send_message(
                chat_id=user_id,
                text=f"👥 **YOUR REFERRAL LINK**\n\n{referral_link}\n\nShare this link to invite friends and earn 50 {CURRENCY} per successful referral!"
            )
            return ConversationHandler.END

        # FIXED: Handle withdrawal method callbacks specifically
        if not data.startswith("wd_method_"):
            await query.edit_message_text("❌ Invalid selection. Please use /withdraw to restart.")
            return ConversationHandler.END

        method = data.replace("wd_method_", "")
        if method not in PAYMENT_METHODS:
            await query.edit_message_text("❌ Invalid payment method. Please try again.")
            return STEP_PAYMENT_METHOD

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
            return STEP_DETAILS

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
        return STEP_AMOUNT

    except Exception as e:
        logger.error(f"Error in handle_payment_method: {e}")
        await query.edit_message_text("❌ Error occurred. Please use /withdraw to restart.")
        return ConversationHandler.END

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle withdrawal amount input."""
    user_id = str(update.effective_user.id)
    message = update.message
    logger.info(f"Amount input from user {user_id}: {message.text}")

    try:
        payment_method = context.user_data.get("payment_method")
        if not payment_method:
            await message.reply_text("❌ Session expired. Please restart with /withdraw")
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
            return STEP_AMOUNT

        # Validate minimum amount
        if amount < MIN_WITHDRAWAL:
            await message.reply_text(
                f"❌ **Amount Too Low**\n\n"
                f"အနည်းဆုံး ငွေထုတ်ပမာဏ: {MIN_WITHDRAWAL} {CURRENCY}\n"
                f"Minimum withdrawal: {MIN_WITHDRAWAL} {CURRENCY}"
            )
            return STEP_AMOUNT

        # Validate maximum daily limit
        if amount > MAX_DAILY_WITHDRAWAL:
            await message.reply_text(
                f"❌ **Amount Too High**\n\n"
                f"နေ့စဉ် အများဆုံး: {MAX_DAILY_WITHDRAWAL:,} {CURRENCY}\n"
                f"Daily maximum: {MAX_DAILY_WITHDRAWAL:,} {CURRENCY}"
            )
            return STEP_AMOUNT

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
            return STEP_AMOUNT

        # Check daily withdrawal limit
        current_time = datetime.now(timezone.utc)
        last_withdrawal = user.get("last_withdrawal")
        withdrawn_today = user.get("withdrawn_today", 0)
        
        # Reset daily limit if it's a new day
        if last_withdrawal and last_withdrawal.date() != current_time.date():
            withdrawn_today = 0

        if withdrawn_today + amount > MAX_DAILY_WITHDRAWAL:
            remaining = MAX_DAILY_WITHDRAWAL - withdrawn_today
            await message.reply_text(
                f"❌ **Daily Limit Exceeded**\n\n"
                f"📊 Withdrawn Today: {withdrawn_today} {CURRENCY}\n"
                f"💎 Remaining Limit: {remaining} {CURRENCY}\n"
                f"🔄 Limit resets at midnight\n\n"
                f"နေ့စဉ် ကန့်သတ်ချက်ကျော်လွန်ပါသည်။"
            )
            return STEP_AMOUNT

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
        else:  # Phone Bill
            detail_prompt = (
                f"📱 **Phone Bill Top-up**\n\n"
                f"💰 Amount: {amount} {CURRENCY}\n\n"
                f"⚠️ **Amount will be deducted when you submit**\n\n"
                f"📞 **သင့်ဖုန်းနံပါတ်ကို ထည့်ပါ:**\n"
                f"Please enter your phone number:\n"
                f"ဥပမာ: 09123456789"
            )

        await message.reply_text(detail_prompt)
        return STEP_DETAILS

    except Exception as e:
        logger.error(f"Error in handle_amount: {e}")
        await message.reply_text("❌ Error occurred. Please restart with /withdraw")
        return ConversationHandler.END

async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle payment details input with ORDER ID SYSTEM"""
    user_id = str(update.effective_user.id)
    logger.info(f"Payment details from user {user_id}")

    try:
        amount = context.user_data.get("withdrawal_amount")
        payment_method = context.user_data.get("payment_method")
        
        if not amount or not payment_method:
            await update.message.reply_text("❌ Session expired. Please restart with /withdraw")
            return ConversationHandler.END

        # Process input (text or image)
        details = None
        photo_file_id = None
        
        if update.message.photo:
            # Handle QR code image
            try:
                photo = update.message.photo[-1]
                photo_file = await photo.get_file()
                photo_file_id = photo.file_id
                details = "QR Code Image Provided"
                logger.info(f"User {user_id} provided QR code image")
            except Exception as e:
                logger.error(f"Error processing photo: {e}")
                await update.message.reply_text("❌ Error processing image. Please try again.")
                return STEP_DETAILS
                
        elif update.message.text:
            details = update.message.text.strip()
            if not details:
                await update.message.reply_text(
                    "❌ **Empty Details**\n\n"
                    "ကျေးဇူးပြု၍ အချက်အလက်များ ထည့်ပါ။\n"
                    "Please provide payment details or send QR image."
                )
                return STEP_DETAILS
        else:
            await update.message.reply_text(
                "❌ **Invalid Input**\n\n"
                "ကျေးဇူးပြု၍ စာသား သို့မဟုတ် QR ပုံ ပို့ပါ။\n"
                "Please send text details or QR image."
            )
            return STEP_DETAILS

        # Get user data and verify balance again
        user = await db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found. Please restart with /start")
            return ConversationHandler.END
            
        current_balance = user.get("balance", 0)
        if current_balance < amount:
            await update.message.reply_text(
                f"❌ **Balance changed during withdrawal process**\n\n"
                f"💰 Current Balance: {int(current_balance)} {CURRENCY}\n"
                f"💸 Requested: {amount} {CURRENCY}\n\n"
                f"Please restart with /withdraw"
            )
            return ConversationHandler.END

        # *** GENERATE UNIQUE ORDER ID ***
        order_id = await get_next_order_id()
        logger.info(f"Generated Order ID {order_id} for user {user_id}")

        # *** IMMEDIATELY DEDUCT BALANCE WHEN REQUEST IS SUBMITTED ***
        new_balance = current_balance - amount
        withdrawn_today = user.get("withdrawn_today", 0) + amount
        
        # Update user balance immediately (BEFORE admin approval)
        success = await db.update_user(user_id, {
            "balance": new_balance,
            "withdrawn_today": withdrawn_today,
        })
        
        if not success:
            await update.message.reply_text("❌ Failed to process withdrawal. Please try again.")
            return ConversationHandler.END

        # Get user's Telegram info
        telegram_user = await context.bot.get_chat(user_id)
        name = (telegram_user.first_name or "") + (" " + telegram_user.last_name if telegram_user.last_name else "")

        # Create admin approval message with ORDER ID
        admin_message = (
            f"🔔 **NEW WITHDRAWAL REQUEST**\n\n"
            f"🆔 **Order ID:** #{order_id}\n"
            f"👤 **User:** {name} ({user_id})\n"
            f"💰 **Amount:** {amount:,} {CURRENCY}\n"
            f"💳 **Method:** {payment_method}\n"
            f"📱 **Details:** {details}\n"
            f"📊 **Previous Balance:** {int(current_balance)} {CURRENCY}\n"
            f"💵 **New Balance:** {int(new_balance)} {CURRENCY}\n"
            f"📝 **User Messages:** {user.get('messages', 0):,}\n"
            f"🎯 **User Level:** {user.get('user_level', 1)}\n"
            f"👥 **Referrals:** {user.get('successful_referrals', 0)}\n"
            f"📅 **Request Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"💡 **Balance already deducted - will refund if rejected**\n"
            f"⏳ **Status:** PENDING APPROVAL"
        )

        # Create admin keyboard with order ID
        keyboard = [
            [
                InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user_id}_{amount}_{order_id}"),
                InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{user_id}_{amount}_{order_id}")
            ],
            [
                InlineKeyboardButton("👤 User Profile", callback_data=f"profile_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send to admin log channel
        try:
            log_msg = await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=admin_message,
                reply_markup=reply_markup
            )
            
            # Send QR image if provided
            if photo_file_id:
                await context.bot.send_photo(
                    chat_id=LOG_CHANNEL_ID,
                    photo=photo_file_id,
                    caption=f"💳 QR Code for Order #{order_id}\nUser: {name} ({user_id})\nAmount: {amount:,} {CURRENCY}",
                    reply_to_message_id=log_msg.message_id
                )
                
        except Exception as e:
            logger.error(f"Failed to send to log channel: {e}")
            # Refund the balance if we can't send to admin
            await db.update_user(user_id, {
                "balance": current_balance,
                "withdrawn_today": withdrawn_today - amount
            })
            await update.message.reply_text("❌ Failed to submit withdrawal request. Balance restored. Please try again.")
            return ConversationHandler.END

        # Update user with pending withdrawal including Order ID
        pending_withdrawal = {
            "order_id": order_id,
            "amount": amount,
            "payment_method": payment_method,
            "details": details,
            "photo_file_id": photo_file_id,
            "status": "PENDING",
            "message_id": log_msg.message_id,
            "request_time": datetime.now(timezone.utc).isoformat(),
            "original_balance": current_balance,
            "balance_deducted": True
        }
        
        current_pending = user.get("pending_withdrawals", [])
        current_pending.append(pending_withdrawal)
        
        await db.update_user(user_id, {
            "pending_withdrawals": current_pending,
            "first_name": telegram_user.first_name,
            "last_name": telegram_user.last_name
        })

        # Success message to user with ORDER ID
        success_message = (
            f"✅ **WITHDRAWAL SUBMITTED SUCCESSFULLY!**\n\n"
            f"🆔 **Order ID:** #{order_id}\n"
            f"💰 **Amount:** {amount:,} {CURRENCY}\n"
            f"💳 **Method:** {payment_method}\n"
            f"📱 **Details:** {details if not photo_file_id else 'QR Code Provided'}\n\n"
            f"💵 **Previous Balance:** {int(current_balance)} {CURRENCY}\n"
            f"💵 **Current Balance:** {int(new_balance)} {CURRENCY}\n\n"
            f"⚠️ **Amount deducted from your balance**\n"
            f"🔄 **Will be refunded if admin rejects**\n"
            f"⏳ **Status:** Pending Admin Approval\n"
            f"⏱️ **Processing Time:** Usually 2-24 hours\n\n"
            f"🔔 **You will be notified when processed.**\n"
            f"📋 **Keep your Order ID for reference: #{order_id}**\n\n"
            f"သင့်ငွေထုတ်မှုကို အောင်မြင်စွာ တင်ပြပြီး လက်ကျန်ငွေမှ နုတ်ယူပါသည်။\n"
            f"Order ID #{order_id} ကို မှတ်သားထားပါ။"
        )
        
        await update.message.reply_text(success_message)
        logger.info(f"Withdrawal request submitted with Order ID {order_id}: User {user_id}, Amount {amount}, Method {payment_method}")

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in handle_details: {e}")
        await update.message.reply_text("❌ Error occurred. Please restart with /withdraw")
        return ConversationHandler.END

async def handle_user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user profile callback from withdrawal requests"""
    query = update.callback_query
    admin_id = str(query.from_user.id)
    data = query.data
    
    if admin_id not in ADMIN_IDS:
        await query.answer("❌ You are not authorized!", show_alert=True)
        return
    
    await query.answer()
    
    try:
        if data.startswith("profile_"):
            target_user_id = data.replace("profile_", "")
            
            # Get detailed user info
            user = await db.get_user(target_user_id)
            if not user:
                await query.answer("❌ User not found!", show_alert=True)
                return
            
            # Calculate user stats
            total_users = await db.get_total_users_count()
            earning_rank = await db.get_user_rank_by_earnings(target_user_id)
            message_rank = await db.get_user_rank(target_user_id, "messages")
            
            # Get user's Telegram info
            try:
                telegram_user = await context.bot.get_chat(target_user_id)
                username = f"@{telegram_user.username}" if telegram_user.username else "No username"
                full_name = (telegram_user.first_name or "") + (" " + telegram_user.last_name if telegram_user.last_name else "")
            except:
                username = "Private"
                full_name = user.get('first_name', 'Unknown') + " " + user.get('last_name', '')
            
            # Get order history
            pending_orders = [w for w in user.get('pending_withdrawals', []) if w.get('status') == 'PENDING']
            completed_orders = [w for w in user.get('pending_withdrawals', []) if w.get('status') == 'APPROVED']
            
            # Create detailed profile
            profile_text = f"""👤 **USER PROFILE DETAILS**

🆔 **Basic Info:**
• User ID: {target_user_id}
• Name: {full_name.strip()}
• Username: {username}
• Status: {'🚫 Banned' if user.get('banned', False) else '✅ Active'}

💰 **Financial Stats:**
• Balance: {int(user.get('balance', 0))} {CURRENCY}
• Total Earned: {int(user.get('total_earnings', 0))} {CURRENCY}
• Total Withdrawn: {int(user.get('total_withdrawn', 0))} {CURRENCY}
• Withdrawn Today: {int(user.get('withdrawn_today', 0))} {CURRENCY}

📊 **Activity Stats:**
• Total Messages: {user.get('messages', 0):,}
• User Level: {user.get('user_level', 1)}
•
