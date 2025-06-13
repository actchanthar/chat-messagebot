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
from config import (
    GROUP_CHAT_IDS,
    WITHDRAWAL_THRESHOLD,
    DAILY_WITHDRAWAL_LIMIT,
    CURRENCY,
    LOG_CHANNEL_ID,
    PAYMENT_METHODS,
    ADMIN_IDS,
    INVITE_THRESHOLD,
)
from database.database import db
import logging
from datetime import datetime, timezone
import traceback

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Conversation states
STEP_PAYMENT_METHOD, STEP_AMOUNT, STEP_DETAILS = range(3)

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the /withdraw command to initiate a withdrawal process."""
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Withdraw command initiated by user {user_id} in chat {chat_id}")

    try:
        # Check if command is used in a private chat
        if update.effective_chat.type != "private":
            error_msg = "ကျေးဇူးပြု၍ /withdraw ကို သီးသန့်ချက်တွင်သာ အသုံးပြုပါ။"
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            logger.warning(f"User {user_id} attempted withdrawal in non-private chat {chat_id}")
            return ConversationHandler.END

        # Retrieve user from database
        user = await db.get_user(user_id)
        if not user:
            error_msg = "အသုံးပြုသူ မတွေ့ပါ။ ကျေးဇူးပြု၍ /start ဖြင့် စတင်ပါ။"
            logger.error(f"User {user_id} not found in database")
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            return ConversationHandler.END

        # Check if user is banned
        if user.get("banned", False):
            error_msg = "သင်သည် ဤဘော့ကို အသုံးပြုခွင့် ပိတ်ပင်ထားပါသည်။"
            logger.info(f"Banned user {user_id} attempted withdrawal")
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            return ConversationHandler.END

        # Check invite threshold
        if user.get("invites", 0) < INVITE_THRESHOLD:
            error_msg = (
                f"You need at least {INVITE_THRESHOLD} invites to withdraw. "
                f"Current invites: {user.get('invites', 0)}."
            )
            logger.info(f"User {user_id} has insufficient invites: {user.get('invites', 0)} < {INVITE_THRESHOLD}")
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            return ConversationHandler.END

        # Check pending withdrawals
        pending_withdrawals = user.get("pending_withdrawals", [])
        pending_count = sum(1 for w in pending_withdrawals if w["status"] == "PENDING")
        if pending_count > 0:
            error_msg = (
                "သင့်တွင် ဆိုင်းငံ့ထားသော ငွေထုတ်မှု ရှိနေပါသည်။ "
                "Admin မှ အတည်ပြုပြီးမှ နောက်ထပ် ငွေထုတ်နိုင်ပါသည်။"
            )
            logger.info(f"User {user_id} has {pending_count} pending withdrawals")
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.reply_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            return ConversationHandler.END

        # Clear user data for fresh withdrawal
        context.user_data.clear()
        logger.debug(f"Cleared user_data for user {user_id}")

        # Create payment method selection keyboard
        keyboard = [[InlineKeyboardButton(method, callback_data=f"method_{method}")] for method in PAYMENT_METHODS]
        keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send payment method selection prompt
        prompt_msg = "ကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။ 💳"
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(prompt_msg, reply_markup=reply_markup)
            await update.callback_query.message.delete()
        else:
            await update.message.reply_text(prompt_msg, reply_markup=reply_markup)
        logger.info(f"Prompted user {user_id} for payment method selection")
        return STEP_PAYMENT_METHOD

    except TelegramError as te:
        logger.error(f"Telegram API error in withdraw for user {user_id}: {te}\n{traceback.format_exc()}")
        error_msg = "A Telegram error occurred. Please try again later."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Unexpected error in withdraw for user {user_id}: {e}\n{traceback.format_exc()}")
        error_msg = "An unexpected error occurred. Please try again later or contact support."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
        return ConversationHandler.END

async def handle_withdraw_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle withdrawal button callback."""
    user_id = str(update.effective_user.id)
    logger.info(f"Withdraw button clicked by user {user_id}")
    try:
        return await withdraw(update, context)
    except Exception as e:
        logger.error(f"Error in handle_withdraw_button for user {user_id}: {e}\n{traceback.format_exc()}")
        await update.callback_query.answer()
        await update.callback_query.message.reply_text("An error occurred. Please try again.")
        return ConversationHandler.END

async def handle_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle payment method selection."""
    query = update.callback_query
    user_id = str(update.effective_user.id)
    data = query.data
    logger.info(f"Payment method selection for user {user_id}, data: {data}")

    try:
        await query.answer()

        if data == "cancel":
            await query.message.reply_text("ငွေထုတ်မှု လုပ်ငန်းစဉ်ကို ပယ်ဖျက်လိုက်ပါပြီ�।")
            logger.info(f"User {user_id} cancelled withdrawal")
            return ConversationHandler.END

        if not data.startswith("method_"):
            logger.warning(f"Invalid callback data for user {user_id}: {data}")
            await query.message.reply_text("ရွေးချယ်မှု မမှန်ကန်ပါ။ ကျေးဇူးပြု၍ /withdraw ဖြင့် ပြန်စတင်ပါ။")
            return ConversationHandler.END

        method = data.replace("method_", "")
        if method not in PAYMENT_METHODS:
            logger.warning(f"Invalid payment method {method} for user {user_id}")
            await query.message.reply_text("ငွေပေးချေမှုနည်းလမ်း မမှန်ကန်ပါ။ ကျေးဇူးပြု၍ ပြန်ကြိုးစားပါ။")
            return STEP_PAYMENT_METHOD

        context.user_data["payment_method"] = method
        logger.info(f"User {user_id} selected payment method: {method}")

        if method == "Phone Bill":
            context.user_data["withdrawal_amount"] = 1000
            await query.message.reply_text(
                "Phone Bill ဖြင့် ငွေထုတ်မှုသည် ၁၀၀၀ ကျပ် ပုံသေဖြစ်ပါသည်။\n"
                "သင့်ဖုန်းနံပါတ်ကို ပေးပို့ပါ (ဥပမာ 09123456789)။"
            )
            return STEP_DETAILS

        await query.message.reply_text(
            f"ငွေထုတ်ရန် ပမာဏကို ထည့်ပါ (အနည်းဆုံး: {WITHDRAWAL_THRESHOLD} {CURRENCY})။"
        )
        return STEP_AMOUNT

    except TelegramError as te:
        logger.error(f"Telegram API error in handle_payment_method for user {user_id}: {te}\n{traceback.format_exc()}")
        await query.message.reply_text("A Telegram error occurred. Please try again.")
        return STEP_PAYMENT_METHOD
    except Exception as e:
        logger.error(f"Unexpected error in handle_payment_method for user {user_id}: {e}\n{traceback.format_exc()}")
        await query.message.reply_text("An unexpected error occurred. Please try again or contact support.")
        return ConversationHandler.END

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle withdrawal amount input."""
    user_id = str(update.effective_user.id)
    message = update.message
    logger.info(f"Received amount input from user {user_id}: {message.text}")

    try:
        payment_method = context.user_data.get("payment_method")
        if not payment_method:
            logger.error(f"No payment method in context for user {user_id}")
            await message.reply_text("အမှား: ငွေပေးချေမှုနည်းလမ်း မရှိပါ။ ကျေးဇူးပြု၍ /withdraw ဖြင့် ပြန်စတင်ပါ။")
            return ConversationHandler.END

        # Parse amount
        amount = int(message.text.strip())
        logger.debug(f"Parsed amount for user {user_id}: {amount}")

        # Validate amount for Phone Bill
        if payment_method == "Phone Bill" and amount != 1000:
            await message.reply_text(
                "Phone Bill ဖြင့် ငွေထုတ်မှုသည် ၁၀၀၀ ကျပ်သာ လုပ်ဆောင်နိုင်ပါသည်။ ကျေးဇူးပြု၍ ၁၀၀၀ ထည့်ပါ။"
            )
            return STEP_AMOUNT

        # Check minimum withdrawal threshold
        if amount < WITHDRAWAL_THRESHOLD:
            await message.reply_text(
                f"အနည်းဆုံး ငွေထုတ်ပမာဏသည် {WITHDRAWAL_THRESHOLD} {CURRENCY} ဖြစ်ပါသည်။ ကျေးဇူးပြု၍ ပြန်ကြိုးစားပါ။"
            )
            return STEP_AMOUNT

        # Retrieve user data
        user = await db.get_user(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            await message.reply_text("အသုံးပြုသူ မတွေ့ပါ။ ကျေးဇူးပြု၍ /start ဖြင့် စတင်ပါ�।")
            return ConversationHandler.END

        # Check pending withdrawals
        pending_withdrawals = user.get("pending_withdrawals", [])
        pending_count = sum(1 for w in pending_withdrawals if w["status"] == "PENDING")
        if pending_count > 0:
            logger.info(f"User {user_id} has {pending_count} pending withdrawals")
            await message.reply_text(
                "သင့်တွင် ဆိုင်းငံ့ထားသော ငွေထုတ်မှု ရှိနေပါသည်။ Admin မှ အတည်ပြုပြီးမှ နောက်ထပ် ငွေထုတ်နိုင်ပါသည်။"
            )
            return ConversationHandler.END

        # Check balance
        balance = user.get("balance", 0)
        if balance < amount:
            logger.info(f"Insufficient balance for user {user_id}: {int(balance)} < {amount}")
            await message.reply_text(
                f"လက်ကျန်ငွေ မလုံလောက်ပါ။ သင့်လက်�ကျန်ငွေသည် {int(balance)} {CURRENCY} ဖြစ်ပါသည်။ /balance ဖြင့် စစ်ဆေးပါ။"
            )
            return STEP_AMOUNT

        # Check daily withdrawal limit
        last_withdrawal = user.get("last_withdrawal")
        withdrawn_today = user.get("withdrawn_today", 0)
        current_time = datetime.now(timezone.utc)
        if last_withdrawal and last_withdrawal.date() == current_time.date():
            if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                logger.info(f"Daily limit exceeded for user {user_id}: {withdrawn_today} + {amount} > {DAILY_WITHDRAWAL_LIMIT}")
                await message.reply_text(
                    f"နေ့စဉ်ထုတ်ယူနိုင်မှု ကန့်သတ်ချက် {DAILY_WITHDRAWAL_LIMIT} {CURRENCY} ကျော်လွန်သွားပါပြီ။ "
                    f"ယနေ့ထုတ်ပြီးပမာဏ: {withdrawn_today} {CURRENCY}။"
                )
                return STEP_AMOUNT

        context.user_data["withdrawal_amount"] = amount
        logger.debug(f"Stored withdrawal amount {amount} for user {user_id}")

        # Prompt for payment details
        if payment_method == "KBZ Pay":
            await message.reply_text(
                "သင့် KBZ Pay အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789 နာမည်) သို့မဟုတ် QR ပုံကို တင်ပါ။"
            )
        elif payment_method == "Wave Pay":
            await message.reply_text(
                "သင့် Wave Pay အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789 နာမည်) သို့မဟုတ် QR ပုံကို တင်ပါ။"
            )
        else:  # Phone Bill
            await message.reply_text(
                "သင့်ဖုန်းနံပါတ်ကို ပေးပို့ပါ (ဥပမာ 09123456789)။"
            )

        logger.info(f"Prompted user {user_id} for payment details (method: {payment_method})")
        return STEP_DETAILS

    except ValueError:
        logger.warning(f"Invalid amount format from user {user_id}: {message.text}")
        await message.reply_text("ကျေးဇူးပြု၍ မှန်ကန်သော နံပါတ်တစ်ခု ထည့်ပါ (ဥပမာ 100)။")
        return STEP_AMOUNT
    except TelegramError as te:
        logger.error(f"Telegram API error in handle_amount for user {user_id}: {te}\n{traceback.format_exc()}")
        await message.reply_text("A Telegram error occurred. Please try again.")
        return STEP_AMOUNT
    except Exception as e:
        logger.error(f"Unexpected error in handle_amount for user {user_id}: {e}\n{traceback.format_exc()}")
        await message.reply_text("အမှားတစ်ခု ဖြစ်ပေါ်ခဲ့ပါသည်။ ကျေးဇူးပြု၍ /withdraw ဖြင့် ပြန်ကြိုးစားပါ။")
        return ConversationHandler.END

async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle payment details input (text or QR image)."""
    user_id = str(update.effective_user.id)
    logger.info(f"Received payment details from user {user_id}")

    try:
        amount = context.user_data.get("withdrawal_amount")
        payment_method = context.user_data.get("payment_method")
        if not amount or not payment_method:
            logger.error(f"Missing amount or method for user {user_id}: {context.user_data}")
            await update.message.reply_text(
                "အမှား: ငွေထုတ်မှု ဒေတာ မမှန်ကန်ပါ။ ကျေးဇူးပြု၍ /withdraw ဖြင့် ပြန်စတင်ပါ။"
            )
            return ConversationHandler.END

        # Process text or photo input
        details = None
        photo_file_id = None
        if update.message.photo:
            try:
                photo_file = await update.message.photo[-1].get_file()
                photo_file_id = photo_file.file_id
                details = "QR Image"
                logger.info(f"User {user_id} uploaded QR image with file_id: {photo_file_id}")
            except TelegramError as te:
                logger.error(f"Telegram API error processing photo for user {user_id}: {te}\n{traceback.format_exc()}")
                await update.message.reply_text("Error processing QR image. Please try again.")
                return STEP_DETAILS
        elif update.message.text:
            details = update.message.text.strip() or "အသေးစိတ် မပေးထားပါ"
            logger.info(f"User {user_id} provided text details: {details}")
        else:
            logger.warning(f"No valid input from user {user_id}")
            await update.message.reply_text("ကျေးဇူးပြု၍ အသေးစိတ် ဖြည့်ပါ သို့မဟုတ် QR ပုံကို တင်ပါ။")
            return STEP_DETAILS

        # Retrieve user data
        user = await db.get_user(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            await update.message.reply_text("အသုံးပြုသူ မတွေ့ပါ။ ကျေးဇူးပြု၍ /start ဖြင့် စတင်ပါ။")
            return ConversationHandler.END

        # Verify balance
        if user.get("balance", 0) < amount:
            logger.info(f"Insufficient balance for user {user_id}: {int(user.get('balance', 0))} < {amount}")
            await update.message.reply_text(
                f"လက်ကျန်ငွေ မလုံလောက်ပါ�। သင့်လက်ကျန်ငွေသည် {int(user.get('balance', 0))} {CURRENCY} ဖြစ်ပါသည်။ /balance ဖြင့် စစ်ဆေးပါ။"
            )
            return ConversationHandler.END

        # Get user name from Telegram
        telegram_user = await context.bot.get_chat(user_id)
        name = (telegram_user.first_name or "") + (" " + telegram_user.last_name if telegram_user.last_name else "")

        # Create admin approval keyboard
        keyboard = [
            [
                InlineKeyboardButton("အတည်ပြုမည် ✅", callback_data=f"approve_{user_id}_{amount}"),
                InlineKeyboardButton("ငြင်းပယ်မည် ❌", callback_data=f"reject_{user_id}_{amount}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Prepare log message
        log_message = (
            f"ငွေထုတ်မှု တောင်းဆိုချက်:\n"
            f"အသုံးပြုသူ ID: {user_id}\n"
            f"နာမည်: {name}\n"
            f"ပမာဏ: {amount} {CURRENCY}\n"
            f"နည်းလမ်း: {payment_method}\n"
            f"အသေးစိတ်: {details if not photo_file_id else 'ပူးတွဲပါ QR ပုံကို ကြည့်ပါ'}\n"
            f"အခြေအနေ: ဆိုင်းငံ့ထားသည် ⏳"
        )

        # Send withdrawal request to log channel
        try:
            log_msg = await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=log_message,
                reply_markup=reply_markup
            )
            if photo_file_id:
                await context.bot.send_photo(
                    chat_id=LOG_CHANNEL_ID,
                    photo=photo_file_id,
                    caption="ငွေထုတ်မှုအတွက် ပူးတွဲပါ QR ပုံ",
                    reply_to_message_id=log_msg.message_id
                )
            await context.bot.pin_chat_message(chat_id=LOG_CHANNEL_ID, message_id=log_msg.message_id)
        except TelegramError as te:
            logger.error(f"Failed to send withdrawal request to log channel for user {user_id}: {te}\n{traceback.format_exc()}")
            await update.message.reply_text("Error submitting withdrawal request. Please try again later.")
            return ConversationHandler.END

        # Update user data with pending withdrawal
        pending_withdrawal = {
            "amount": amount,
            "payment_method": payment_method,
            "details": details if not photo_file_id else f"QR Image: {photo_file_id}",
            "status": "PENDING",
            "message_id": log_msg.message_id,
            "request_time": datetime.now(timezone.utc)
        }
        success = await db.update_user(user_id, {
            "pending_withdrawals": user.get("pending_withdrawals", []) + [pending_withdrawal],
            "first_name": telegram_user.first_name,
            "last_name": telegram_user.last_name
        })
        if not success:
            logger.error(f"Failed to update user {user_id} with pending withdrawal")
            await update.message.reply_text("Error recording withdrawal request. Please try again.")
            return ConversationHandler.END

        # Notify user
        await update.message.reply_text(
            f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို တင်ပြခဲ့ပါသည်။ Admin ၏ အတည်ပြုချက်ကို စောင့်ပါ။ ⏳"
        )
        logger.info(f"Withdrawal request submitted for user {user_id}: {amount} {CURRENCY} via {payment_method}")

        return ConversationHandler.END

    except TelegramError as te:
        logger.error(f"Telegram API error in handle_details for user {user_id}: {te}\n{traceback.format_exc()}")
        await update.message.reply_text("A Telegram error occurred. Please try again.")
        return STEP_DETAILS
    except Exception as e:
        logger.error(f"Unexpected error in handle_details for user {user_id}: {e}\n{traceback.format_exc()}")
        await update.message.reply_text("အမှားတစ်ခု ဖြစ်ပေါ်ခဲ့ပါသည်။ ကျေးဇူးပြု၍ /withdraw ဖြင့် ပြန်ကြိုးစားပါ။")
        return ConversationHandler.END

async def handle_approval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin approval or rejection of withdrawal requests."""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    logger.info(f"Approval callback for admin {user_id}, data: {data}")

    try:
        if user_id not in ADMIN_IDS:
            await query.answer(text="You are not authorized to perform this action.")
            logger.warning(f"Unauthorized approval attempt by user {user_id}")
            return

        await query.answer()

        if not data.startswith(("approve_", "reject_")):
            logger.warning(f"Invalid callback data for admin {user_id}: {data}")
            await query.message.reply_text("Invalid action. Please use the provided buttons.")
            return

        action, target_user_id, amount = data.split("_", 2)
        amount = int(amount)
        status = "APPROVED" if action == "approve" else "REJECTED"
        status_emoji = "✅" if status == "APPROVED" else "❌"
        status_text = "အတည်ပြုပြီး" if status == "APPROVED" else "ငြင်းပယ်လိုက်သည်"

        # Retrieve target user
        user = await db.get_user(target_user_id)
        if not user:
            logger.error(f"Target user {target_user_id} not found")
            await query.message.reply_text(f"User {target_user_id} not found.")
            return

        # Find and update pending withdrawal
        pending_withdrawals = user.get("pending_withdrawals", [])
        withdrawal = None
        for w in pending_withdrawals:
            if w["amount"] == amount and w["status"] == "PENDING" and w["message_id"] == query.message.message_id:
                withdrawal = w
                break

        if not withdrawal:
            logger.warning(f"No matching pending withdrawal found for user {target_user_id}, amount {amount}")
            await query.message.reply_text("No matching pending withdrawal found.")
            return

        # Update withdrawal status
        withdrawal["status"] = status
        if status == "APPROVED":
            balance = user.get("balance", 0)
            if balance < amount:
                logger.warning(f"Insufficient balance for user {target_user_id}: {balance} < {amount}")
                await query.message.reply_text(f"User {target_user_id} has insufficient balance.")
                return
            new_balance = balance - amount
            withdrawn_today = user.get("withdrawn_today", 0)
            await db.update_user(target_user_id, {
                "balance": new_balance,
                "pending_withdrawals": pending_withdrawals,
                "last_withdrawal": datetime.now(timezone.utc),
                "withdrawn_today": withdrawn_today + amount
            })
        else:
            await db.update_user(target_user_id, {
                "pending_withdrawals": pending_withdrawals
            })

        # Update log message
        updated_log_message = query.message.text + f"\n\nUpdated: {status_text} {status_emoji} by Admin {user_id}"
        await query.message.edit_text(updated_log_message)

        # Notify user
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို {status_text.lower()}ပါသည်။ {status_emoji}\n"
                    f"အကြောင်းအမျိုးမျိုး: {'Admin decision' if status == 'REJECTED' else 'Successful withdrawal'}"
                )
            )
            logger.info(f"Notified user {target_user_id} of {status.lower()} withdrawal: {amount} {CURRENCY}")
        except TelegramError as te:
            logger.error(f"Failed to notify user {target_user_id} of withdrawal status: {te}\n{traceback.format_exc()}")

        logger.info(f"Admin {user_id} {status.lower()} withdrawal for user {target_user_id}: {amount} {CURRENCY}")

    except ValueError as ve:
        logger.error(f"Value error in handle_approval for admin {user_id}: {ve}\n{traceback.format_exc()}")
        await query.message.reply_text("Invalid data format. Please check the request.")
    except TelegramError as te:
        logger.error(f"Telegram API error in handle_approval for admin {user_id}: {te}\n{traceback.format_exc()}")
        await query.message.reply_text("A Telegram error occurred. Please try again.")
    except Exception as e:
        logger.error(f"Unexpected error in handle_approval for admin {user_id}: {e}\n{traceback.format_exc()}")
        await query.message.reply_text("An unexpected error occurred. Please try again or contact support.")

def register_handlers(application: Application):
    """Register all handlers for the withdrawal conversation."""
    logger.info("Registering withdrawal handlers")
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
        allow_reentry=True
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_approval, pattern="^(approve_|reject_)"))