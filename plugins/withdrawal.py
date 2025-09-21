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

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config import (
    MIN_WITHDRAWAL,
    MAX_DAILY_WITHDRAWAL,
    CURRENCY,
    LOG_CHANNEL_ID,
    ADMIN_IDS,
    APPROVED_GROUPS
)
from database.database import db

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
STEP_PAYMENT_METHOD, STEP_AMOUNT, STEP_DETAILS = range(3)

# Payment methods
PAYMENT_METHODS = ["KBZ Pay", "Wave Pay", "AYA Pay", "CB Pay", "Phone Bill"]

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

        # FIXED: Check minimum message requirement BUT SKIP FOR ADMIN/OWNER
        is_admin_or_owner = user_id in ADMIN_IDS
        messages_count = user.get("messages", 0)
        
        if not is_admin_or_owner and messages_count < 50:  # Only check for regular users
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
                "Admin မှ အတည်ပြုပြီးမှ နောက်ထပ် ငွေထုတ်နိုင်ပါသည်။\n\n"
                "You have pending withdrawal requests. Please wait for admin approval."
            )
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            return ConversationHandler.END

        # Clear user data for fresh withdrawal
        context.user_data.clear()

        # Create payment method selection keyboard
        keyboard = []
        for method in PAYMENT_METHODS:
            keyboard.append([InlineKeyboardButton(f"💳 {method}", callback_data=f"method_{method}")])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send payment method selection prompt
        current_balance = user.get("balance", 0)
        
        # Special message for admin/owner
        admin_note = f"\n👑 **ADMIN ACCESS** - Message requirement bypassed!" if is_admin_or_owner else ""
        
        prompt_msg = (
            f"💸 **WITHDRAWAL REQUEST**\n\n"
            f"💰 **Current Balance:** {int(current_balance)} {CURRENCY}\n"
            f"💎 **Minimum:** {MIN_WITHDRAWAL} {CURRENCY}\n"
            f"📈 **Daily Limit:** {MAX_DAILY_WITHDRAWAL:,} {CURRENCY}{admin_note}\n\n"
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

async def handle_withdraw_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle withdrawal button callback from start menu."""
    logger.info(f"Withdraw button clicked by user {update.callback_query.from_user.id}")
    return await withdraw(update, context)

async def handle_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle payment method selection."""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    logger.info(f"Payment method selection for user {user_id}: {data}")

    try:
        await query.answer()

        if data == "cancel":
            await query.edit_message_text(
                "❌ **Withdrawal Cancelled**\n\n"
                "ငွေထုတ်မှု လုပ်ငန်းစဉ်ကို ပယ်ဖျက်လိုက်ပါပြီ။\n"
                "Use /withdraw to start again anytime."
            )
            return ConversationHandler.END

        if not data.startswith("method_"):
            await query.edit_message_text("❌ Invalid selection. Please use /withdraw to restart.")
            return ConversationHandler.END

        method = data.replace("method_", "")
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
            f"💸 **ငွေထုတ်ရန် ပမာဏကို ထည့်ပါ:**\n"
            f"Please enter the amount to withdraw:"
        )
        return STEP_AMOUNT

    except Exception as e:
        logger.error(f"Error in handle_payment_method: {e}")
        await query.edit_message_text("❌ Error occurred. Please use /withdraw to restart.")
        return ConversationHandler.END

# ... Rest of the withdrawal.py code remains the same as before ...

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

        context.user_data["withdrawal_amount"] = amount

        # Prompt for payment details
        detail_prompt = (
            f"🏦 **Payment Details Required**\n\n"
            f"💰 Amount: {amount} {CURRENCY}\n"
            f"💳 Method: {payment_method}\n\n"
            f"📱 **Please provide:**\n"
            f"• Phone number (09XXXXXXXX)\n"
            f"• Account holder name\n"
            f"• OR send QR code image\n\n"
            f"ဥပမာ: 09123456789 Your Name"
        )

        await message.reply_text(detail_prompt)
        return STEP_DETAILS

    except Exception as e:
        logger.error(f"Error in handle_amount: {e}")
        await message.reply_text("❌ Error occurred. Please restart with /withdraw")
        return ConversationHandler.END

async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle payment details input (text or QR image)."""
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

        # Get user's Telegram info
        telegram_user = await context.bot.get_chat(user_id)
        name = (telegram_user.first_name or "") + (" " + telegram_user.last_name if telegram_user.last_name else "")

        # Create admin approval message
        admin_message = (
            f"🔔 **NEW WITHDRAWAL REQUEST**\n\n"
            f"👤 **User:** {name} ({user_id})\n"
            f"💰 **Amount:** {amount:,} {CURRENCY}\n"
            f"💳 **Method:** {payment_method}\n"
            f"📱 **Details:** {details}\n"
            f"📅 **Request Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"⏳ **Status:** PENDING APPROVAL"
        )

        # Create admin keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user_id}_{amount}"),
                InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{user_id}_{amount}")
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
                    caption=f"💳 QR Code for withdrawal request\nUser: {name} ({user_id})",
                    reply_to_message_id=log_msg.message_id
                )
                
        except Exception as e:
            logger.error(f"Failed to send to log channel: {e}")
            await update.message.reply_text("❌ Failed to submit withdrawal request. Please try again.")
            return ConversationHandler.END

        # Update user with pending withdrawal
        pending_withdrawal = {
            "amount": amount,
            "payment_method": payment_method,
            "details": details,
            "photo_file_id": photo_file_id,
            "status": "PENDING",
            "message_id": log_msg.message_id,
            "request_time": datetime.now(timezone.utc).isoformat()
        }
        
        current_pending = user.get("pending_withdrawals", [])
        current_pending.append(pending_withdrawal)
        
        await db.update_user(user_id, {
            "pending_withdrawals": current_pending,
            "first_name": telegram_user.first_name,
            "last_name": telegram_user.last_name
        })

        # Success message to user
        success_message = (
            f"✅ **WITHDRAWAL SUBMITTED SUCCESSFULLY!**\n\n"
            f"🆔 **Request ID:** WD-{log_msg.message_id}\n"
            f"💰 **Amount:** {amount:,} {CURRENCY}\n"
            f"💳 **Method:** {payment_method}\n"
            f"📱 **Details:** {details if not photo_file_id else 'QR Code Provided'}\n\n"
            f"⏳ **Status:** Pending Admin Approval\n"
            f"⏱️ **Processing Time:** Usually 2-24 hours\n\n"
            f"🔔 **You will be notified when processed.**\n\n"
            f"သင့်ငွေထုတ်မှုကို အောင်မြင်စွာ တင်ပြပါသည်။\n"
            f"Admin ၏ အတည်ပြုချက်ကို စောင့်ပါ။"
        )
        
        await update.message.reply_text(success_message)
        logger.info(f"Withdrawal request submitted: User {user_id}, Amount {amount}, Method {payment_method}")

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in handle_details: {e}")
        await update.message.reply_text("❌ Error occurred. Please restart with /withdraw")
        return ConversationHandler.END

async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin approval/rejection of withdrawal requests."""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    if user_id not in ADMIN_IDS:
        await query.answer("❌ You are not authorized!", show_alert=True)
        return

    await query.answer()
    
    try:
        if data.startswith("approve_") or data.startswith("reject_"):
            parts = data.split("_")
            action = parts[0]
            target_user_id = parts[1]
            amount = int(parts[2])
            
            # Process the withdrawal
            user = await db.get_user(target_user_id)
            if not user:
                await query.edit_message_text("❌ User not found.")
                return

            # Find the pending withdrawal
            pending_withdrawals = user.get("pending_withdrawals", [])
            withdrawal = None
            
            for i, w in enumerate(pending_withdrawals):
                if (w["amount"] == amount and 
                    w["status"] == "PENDING" and 
                    w.get("message_id") == query.message.message_id):
                    withdrawal = w
                    withdrawal_index = i
                    break

            if not withdrawal:
                await query.edit_message_text("❌ Withdrawal request not found.")
                return

            if action == "approve":
                # Check balance again
                if user.get("balance", 0) < amount:
                    await query.edit_message_text("❌ User has insufficient balance!")
                    return

                # Approve withdrawal - deduct balance
                new_balance = user.get("balance", 0) - amount
                withdrawn_today = user.get("withdrawn_today", 0) + amount
                total_withdrawn = user.get("total_withdrawn", 0) + amount
                
                # Update withdrawal status
                pending_withdrawals[withdrawal_index]["status"] = "APPROVED"
                pending_withdrawals[withdrawal_index]["approved_by"] = user_id
                pending_withdrawals[withdrawal_index]["approved_at"] = datetime.now(timezone.utc).isoformat()
                
                await db.update_user(target_user_id, {
                    "balance": new_balance,
                    "withdrawn_today": withdrawn_today,
                    "total_withdrawn": total_withdrawn,
                    "last_withdrawal": datetime.now(timezone.utc),
                    "pending_withdrawals": pending_withdrawals
                })

                # Update admin message
                updated_message = query.message.text + f"\n\n✅ **APPROVED** by Admin {user_id}\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                await query.edit_message_text(updated_message)

                # Notify user
                try:
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=(
                            f"✅ **WITHDRAWAL APPROVED!**\n\n"
                            f"💰 **Amount:** {amount:,} {CURRENCY}\n"
                            f"💳 **Method:** {withdrawal['payment_method']}\n"
                            f"💵 **New Balance:** {int(new_balance)} {CURRENCY}\n\n"
                            f"🎉 Your withdrawal has been processed successfully!\n"
                            f"သင့်ငွေထုတ်မှုကို အတည်ပြုပါသည်။"
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user {target_user_id}: {e}")

            else:  # reject
                # Update withdrawal status
                pending_withdrawals[withdrawal_index]["status"] = "REJECTED"
                pending_withdrawals[withdrawal_index]["rejected_by"] = user_id
                pending_withdrawals[withdrawal_index]["rejected_at"] = datetime.now(timezone.utc).isoformat()
                
                await db.update_user(target_user_id, {
                    "pending_withdrawals": pending_withdrawals
                })

                # Update admin message
                updated_message = query.message.text + f"\n\n❌ **REJECTED** by Admin {user_id}\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                await query.edit_message_text(updated_message)

                # Notify user
                try:
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=(
                            f"❌ **WITHDRAWAL REJECTED**\n\n"
                            f"💰 **Amount:** {amount:,} {CURRENCY}\n"
                            f"💳 **Method:** {withdrawal['payment_method']}\n\n"
                            f"📝 Your withdrawal request was not approved.\n"
                            f"💡 Please contact support if you have questions.\n\n"
                            f"သင့်ငွေထုတ်မှုကို ငြင်းပယ်ပါသည်။"
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user {target_user_id}: {e}")

    except Exception as e:
        logger.error(f"Error in handle_approval: {e}")
        await query.edit_message_text("❌ Error processing withdrawal decision.")

def register_handlers(application: Application):
    """Register all withdrawal handlers."""
    logger.info("Registering withdrawal conversation handlers")
    
    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("withdraw", withdraw),
            CallbackQueryHandler(handle_withdraw_button, pattern="^withdraw$")
        ],
        states={
            STEP_PAYMENT_METHOD: [
                CallbackQueryHandler(handle_payment_method)
            ],
            STEP_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)
            ],
            STEP_DETAILS: [
                MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_details)
            ],
        },
        fallbacks=[
            CommandHandler("withdraw", withdraw),
            CallbackQueryHandler(handle_payment_method, pattern="^cancel$")
        ],
        allow_reentry=True,
        name="withdrawal_conversation",
        persistent=False
    )
    
    # Register handlers
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_approval, pattern="^(approve_|reject_)"))
    
    logger.info("✅ Withdrawal handlers registered successfully")
