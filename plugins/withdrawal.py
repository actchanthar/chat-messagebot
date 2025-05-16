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
from config import GROUP_CHAT_IDS, WITHDRAWAL_THRESHOLD, DAILY_WITHDRAWAL_LIMIT, CURRENCY, LOG_CHANNEL_ID, PAYMENT_METHODS, ADMIN_IDS
from database.database import db
import logging
from datetime import datetime, timezone

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define withdrawal steps
STEP_PAYMENT_METHOD, STEP_AMOUNT, STEP_DETAILS = range(3)

# Handle /balance command and Check Balance button
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Balance function called for user {user_id} in chat {chat_id} via {'button' if update.callback_query else 'command'}")

    if update.callback_query:
        await update.callback_query.answer()

    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        message = "User not found. Please start with /start."
        if update.callback_query:
            await update.callback_query.message.reply_text(message)
        else:
            await update.message.reply_text(message)
        return

    balance = user.get("balance", 0)
    message = f"Your balance: {balance} {CURRENCY}"
    if update.callback_query:
        await update.callback_query.message.edit_text(message)
    else:
        await update.message.reply_text(message)

# Entry point for /withdraw command and Withdraw button
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    source = "command" if update.message else "button"
    logger.info(f"Withdraw function called for user {user_id} in chat {chat_id} via {source}")

    if update.callback_query:
        await update.callback_query.answer()

    if update.effective_chat.type != "private":
        logger.info(f"User {user_id} attempted withdrawal in non-private chat {chat_id}")
        if update.message:
            await update.message.reply_text("Please use the /withdraw command in a private chat.")
        else:
            await update.callback_query.message.reply_text("Please use /withdraw in a private chat.")
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        if update.message:
            await update.message.reply_text("User not found. Please start with /start.")
        else:
            await update.callback_query.message.reply_text("User not found. Please start with /start.")
        return ConversationHandler.END

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        if update.message:
            await update.message.reply_text("You are banned from using this bot.")
        else:
            await update.callback_query.message.reply_text("You are banned from using this bot.")
        return ConversationHandler.END

    # Check invite requirement only for non-admins
    if str(user_id) not in ADMIN_IDS:
        can_withdraw, reason = await db.can_withdraw(user_id)
        if not can_withdraw:
            logger.info(f"User {user_id} cannot withdraw: {reason}")
            if update.message:
                await update.message.reply_text(reason)
            else:
                await update.callback_query.message.reply_text(reason)
            return ConversationHandler.END

    # Check for pending withdrawals
    pending_withdrawals = user.get("pending_withdrawals", [])
    if pending_withdrawals:
        logger.info(f"User {user_id} has a pending withdrawal: {pending_withdrawals}")
        if update.message:
            await update.message.reply_text("You have a pending withdrawal request. Please wait for it to be processed before requesting another.\n"
                                           "သင့်တွင် ဆိုင်းငံ့ထားသော ငွေထုတ်တောင်းဆိုမှုရှိပါသည်။ နောက်တစ်ကြိမ်တောင်းဆိုခြင်းမပြုမီ ပြီးစီးရန်စောင့်ပါ။")
        else:
            await update.callback_query.message.reply_text("You have a pending withdrawal request. Please wait for it to be processed before requesting another.\n"
                                                           "သင့်တွင် ဆိုင်းငံ့ထားသော ငွေထုတ်တောင်းဆိုမှုရှိပါသည်။ နောက်တစ်ကြိမ်တောင်းဆိုခြင်းမပြုမီ ပြီးစီးရန်စောင့်ပါ။")
        return ConversationHandler.END

    context.user_data.clear()
    logger.info(f"Cleared user_data for user {user_id} before starting withdrawal process")

    keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(
            "Please select a payment method: 💳\nကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။",
            reply_markup=reply_markup
        )
    else:
        await update.callback_query.message.reply_text(
            "Please select a payment method: 💳\nကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။",
            reply_markup=reply_markup
        )
    logger.info(f"User {user_id} prompted for payment method selection with buttons: {PAYMENT_METHODS}")
    return STEP_PAYMENT_METHOD

# Handle payment method selection
async def handle_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = query.data
    logger.info(f"Handling payment method selection for user {user_id}, data: {data}")

    if not data.startswith("payment_"):
        logger.error(f"Invalid payment method callback data for user {user_id}: {data}")
        await query.message.reply_text("Invalid payment method. Please start again with /withdraw.")
        return ConversationHandler.END

    method = data.replace("payment_", "")
    if method not in PAYMENT_METHODS:
        logger.info(f"User {user_id} selected invalid payment method: {method}")
        await query.message.reply_text("Invalid payment method selected. Please try again.")
        return STEP_PAYMENT_METHOD

    context.user_data["payment_method"] = method
    logger.info(f"User {user_id} selected payment method {method}, context: {context.user_data}")

    if method == "Phone Bill":
        context.user_data["withdrawal_amount"] = 1000
        await query.message.reply_text(
            "Phone Bill withdrawals are fixed at 1000 kyat for top-up.\n"
            "Please provide your phone number for Phone Bill payment. 💳\n"
            "ကျေးဇူးပြု၍ ဖုန်းဘေလ်ငွေပေးချေမှုအတွက် သင့်ဖုန်းနံပါတ်ကို ပေးပါ။"
        )
        logger.info(f"User {user_id} selected Phone Bill, fixed amount to 1000 kyat")
        return STEP_DETAILS

    await query.message.reply_text(
        f"Please enter the amount you wish to withdraw (minimum: {WITHDRAWAL_THRESHOLD} {CURRENCY}). 💸\n"
        f"ငွေထုတ်ရန် ပမာဏကိုရေးပို့ပါ အနည်းဆုံး {WITHDRAWAL_THRESHOLD} ပြည့်မှထုတ်လို့ရမှာပါ"
    )
    return STEP_AMOUNT

# Handle withdrawal amount input
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    message = update.message
    logger.info(f"Received message for amount input from user {user_id} in chat {chat_id}: {message.text}, context: {context.user_data}")

    payment_method = context.user_data.get("payment_method")
    if not payment_method:
        logger.error(f"User {user_id} missing payment method in context")
        await message.reply_text("Error: Payment method not found. Please start again with /withdraw.")
        return ConversationHandler.END

    try:
        amount = int(message.text.strip())
        if amount < WITHDRAWAL_THRESHOLD:
            await message.reply_text(
                f"Minimum withdrawal amount is {WITHDRAWAL_THRESHOLD} {CURRENCY}. Please try again.\n"
                f"အနည်းဆုံး {WITHDRAWAL_THRESHOLD} {CURRENCY} ထုတ်နိုင်ပါသည်။ ထပ်စမ်းကြည့်ပါ။"
            )
            return STEP_AMOUNT

        user = await db.get_user(user_id)
        if not user:
            await message.reply_text("User not found. Please start again with /start.")
            return ConversationHandler.END

        # Check daily withdrawal limit
        last_withdrawal = user.get("last_withdrawal")
        withdrawn_today = user.get("withdrawn_today", 0)
        current_time = datetime.now(timezone.utc)
        if last_withdrawal:
            last_withdrawal_date = last_withdrawal.date()
            current_date = current_time.date()
            if last_withdrawal_date == current_date:
                if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                    logger.info(f"User {user_id} exceeded daily limit. Withdrawn today: {withdrawn_today}, Requested: {amount}")
                    await message.reply_text(
                        f"User has exceeded the daily withdrawal limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}. "
                        f"You've already withdrawn {withdrawn_today} {CURRENCY} today.\n"
                        f"သင်သည် နေ့စဉ်ထုတ်ယူနိုင်မှု ကန့်သတ်ချက် {DAILY_WITHDRAWAL_LIMIT} {CURRENCY} ကို ကျော်လွန်သွားပါသည်။ "
                        f"သင်သည် ယနေ့အတွက် {withdrawn_today} {CURRENCY} ထုတ်ယူပြီးပါသည်။"
                    )
                    return STEP_AMOUNT
            else:
                withdrawn_today = 0

        # Strict balance check
        if user.get("balance", 0) < amount:
            await message.reply_text(
                "Insufficient balance. Please check your balance with /balance.\n"
                "လက်ကျန်ငွေ မလုံလောက်ပါ။ ကျေးဇူးပြု၍ သင့်လက်ကျန်ငွေကို /balance ဖြင့် စစ်ဆေးပါ။"
            )
            return ConversationHandler.END

        context.user_data["withdrawal_amount"] = amount
        context.user_data["withdrawn_today"] = withdrawn_today
        logger.info(f"Stored withdrawal amount {amount} for user {user_id}, context: {context.user_data}")

        if payment_method == "KBZ Pay":
            await message.reply_text(
                "Please provide your KBZ Pay account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW). 💳\n"
                "ကျေးဇူးပြု၍ သင်၏ KBZ Pay အကောင့်အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789 ZAYAR KO KO MIN ZAW)။"
            )
        elif payment_method == "Wave Pay":
            await message.reply_text(
                "Please provide your Wave Pay account details (e.g., phone number and name). 💳\n"
                "ကျေးဇူးပြု၍ သင်၏ Wave Pay အကောင့်အသေးစိတ်ကို ပေးပါ (ဥပမာ ဖုန်းနံပါတ်နှင့် နာမည်)။"
            )
        else:
            await message.reply_text(
                f"Please provide your {payment_method} account details. 💳\n"
                f"ကျေးဇူးပြု၍ သင်၏ {payment_method} အကောင့်အသေးစိတ်ကို ပေးပါ။"
            )
        logger.info(f"User {user_id} prompted for {payment_method} account details")
        return STEP_DETAILS

    except ValueError:
        await message.reply_text(
            "Please enter a valid number (e.g., 100).\n"
            "ကျေးဇူးပြု၍ မှန်ကန်သော နံပါတ်ထည့်ပါ (ဥပမာ 100)။"
        )
        return STEP_AMOUNT

# Handle account details input
async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    message = update.message
    logger.info(f"Handling account details for user {user_id}: {message.text}")

    amount = context.user_data.get("withdrawal_amount")
    payment_method = context.user_data.get("payment_method")
    withdrawn_today = context.user_data.get("withdrawn_today", 0)
    if not amount or not payment_method:
        logger.error(f"User {user_id} missing amount or payment method in context: {context.user_data}")
        await message.reply_text("Error: Withdrawal amount or payment method not found. Please start again with /withdraw.")
        return ConversationHandler.END

    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        await message.reply_text("User not found. Please start again with /start.")
        return ConversationHandler.END

    # Deduct amount immediately and store as pending
    balance = user.get("balance", 0)
    if balance < amount:
        await message.reply_text(
            "Insufficient balance. Please check your balance with /balance.\n"
            "လက်ကျန်ငွေ မလုံလောက်ပါ။ ကျေးဇူးပြု၍ သင့်လက်ကျန်ငွေကို /balance ဖြင့် စစ်ဆေးပါ။"
        )
        return ConversationHandler.END

    new_balance = balance - amount
    payment_details = message.text if message.text else "No details provided"
    pending_withdrawal = {
        "amount": amount,
        "payment_method": payment_method,
        "payment_details": payment_details,
        "status": "pending",
        "requested_at": datetime.now(timezone.utc)
    }
    result = await db.update_user(user_id, {
        "balance": new_balance,
        "pending_withdrawals": [pending_withdrawal]  # Store as a list for potential future multiple pending withdrawals
    })
    if not result:
        logger.error(f"Failed to deduct amount for user {user_id} during withdrawal request")
        await message.reply_text("Error submitting request. Please try again later.")
        return ConversationHandler.END

    logger.info(f"Deducted {amount} from user {user_id}'s balance. New balance: {new_balance}")
    context.user_data["withdrawal_details"] = payment_details
    logger.info(f"User {user_id} submitted account details, context: {context.user_data}")

    keyboard = [
        [
            InlineKeyboardButton("Approve ✅", callback_data=f"approve_withdrawal_{user_id}_{amount}"),
            InlineKeyboardButton("Reject ❌", callback_data=f"reject_withdrawal_{user_id}_{amount}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    user_first_name = user.get("name", update.effective_user.first_name or "Unknown")
    username = update.effective_user.username or user.get("username", "N/A")
    log_message = (
        f"Withdrawal Request:\n"
        f"{user_first_name}\n"
        f"User ID: {user_id}\n"
        f"Username: @{username}\n"
        f"Amount: {amount} {CURRENCY} 💸\n"
        f"Payment Method: **{payment_method}**\n"
        f"Details: {payment_details}\n"
        f"Invited Users: {user.get('invited_users', 0)}\n"
        f"Status: PENDING ⏳"
    )

    try:
        log_msg = await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=log_message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        await context.bot.pin_chat_message(
            chat_id=LOG_CHANNEL_ID,
            message_id=log_msg.message_id,
            disable_notification=True
        )
        # Store the message ID in context for later editing
        if 'log_message_ids' not in context.chat_data:
            context.chat_data['log_message_ids'] = {}
        context.chat_data['log_message_ids'][user_id] = log_msg.message_id
        logger.info(f"Sent and pinned withdrawal request to log channel {LOG_CHANNEL_ID} for user {user_id} with message ID {log_msg.message_id}")
    except Exception as e:
        # Refund the amount if we can't send the request to the log channel
        await db.update_user(user_id, {
            "balance": balance,
            "pending_withdrawals": []
        })
        logger.error(f"Failed to send or pin withdrawal request to log channel {LOG_CHANNEL_ID} for user {user_id}: {e}")
        await message.reply_text("Error submitting request. Please try again later.")
        return ConversationHandler.END

    await message.reply_text(
        f"Your withdrawal request for {amount} {CURRENCY} has been submitted. The amount has been deducted from your balance and will be processed by an admin. Your new balance is {new_balance} {CURRENCY}. ⏳\n"
        f"သင့်ငွေထုတ်မှု တောင်းဆိုမှု {amount} {CURRENCY} ကို တင်ပြခဲ့ပါသည်။ ပမာဏကို သင့်လက်ကျန်မှ နုတ်ယူလိုက်ပြီး အုပ်ချုပ်ရေးမှူးမှ ဆောင်ရွက်ပေးပါမည်။ သင့်လက်ကျန်ငွေ အသစ်မှာ {new_balance} {CURRENCY} ဖြစ်ပါသည်။"
    )
    logger.info(f"User {user_id} submitted withdrawal request for {amount} {CURRENCY}")

    return ConversationHandler.END

# Handle admin approval/rejection
async def handle_admin_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"Admin receipt callback for user {query.from_user.id}, data: {data}")

    try:
        if data.startswith("approve_withdrawal_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data format: {data}")
                await query.message.reply_text("Error processing withdrawal request.")
                return
            _, _, user_id, amount = parts
            user_id = user_id
            amount = int(amount)

            user = await db.get_user(user_id)
            if not user:
                logger.error(f"User {user_id} not found for withdrawal approval")
                await query.message.reply_text("User not found.")
                return

            result = await db.update_user(user_id, {
                "pending_withdrawals": [],
                "last_withdrawal": datetime.now(timezone.utc),
                "withdrawn_today": user.get("withdrawn_today", 0) + amount
            })
            logger.info(f"db.update_user returned: {result}")

            if result and (isinstance(result, bool) or (hasattr(result, 'modified_count') and result.modified_count > 0)):
                logger.info(f"Withdrawal approved for user {user_id}. Amount: {amount}")
                message_id = context.chat_data.get('log_message_ids', {}).get(user_id)
                if message_id:
                    user_first_name = user.get("name", "Unknown")
                    username = user.get("username", "N/A")
                    updated_message = (
                        f"Withdrawal Request:\n"
                        f"{user_first_name}\n"
                        f"User ID: {user_id}\n"
                        f"Username: @{username}\n"
                        f"Amount: {amount} {CURRENCY} 💸\n"
                        f"Payment Method: **{context.user_data.get('payment_method', 'N/A')}**\n"
                        f"Details: {context.user_data.get('withdrawal_details', 'N/A')}\n"
                        f"Invited Users: {user.get('invited_users', 0)}\n"
                        f"Status: Approve ✅"
                    )
                    try:
                        await context.bot.edit_message_text(
                            chat_id=LOG_CHANNEL_ID,
                            message_id=message_id,
                            text=updated_message,
                            parse_mode="Markdown"
                        )
                        logger.info(f"Updated log channel message {message_id} to 'Approve' for user {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to edit log channel message {message_id} for user {user_id}: {e}")

                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"Your withdrawal of {amount} {CURRENCY} has been approved!\n"
                             f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို အတည်ပြုပြီးပါပြီ။"
                    )
                    logger.info(f"Notified user {user_id} of withdrawal approval")
                except Exception as e:
                    logger.error(f"Failed to notify user {user_id} of withdrawal approval: {e}")

                await query.message.reply_text("Approve done ✅")
                logger.info(f"Confirmed approval to admin for user {user_id}")
            else:
                logger.error(f"Failed to clear pending withdrawal for user {user_id}. Result: {result}")
                await query.message.reply_text("Error approving withdrawal. Please try again.")

        elif data.startswith("reject_withdrawal_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data format: {data}")
                await query.message.reply_text("Error processing withdrawal request.")
                return
            _, _, user_id, amount = parts
            user_id = user_id
            amount = int(amount)

            user = await db.get_user(user_id)
            if not user:
                logger.error(f"User {user_id} not found for withdrawal rejection")
                await query.message.reply_text("User not found.")
                return

            # Refund the amount since the withdrawal is rejected
            balance = user.get("balance", 0)
            new_balance = balance + amount
            result = await db.update_user(user_id, {
                "balance": new_balance,
                "pending_withdrawals": []
            })
            logger.info(f"db.update_user returned: {result} for user {user_id} on rejection")

            # Update log channel message
            message_id = context.chat_data.get('log_message_ids', {}).get(user_id)
            if message_id:
                user_first_name = user.get("name", "Unknown")
                username = user.get("username", "N/A")
                updated_message = (
                    f"Withdrawal Request:\n"
                    f"{user_first_name}\n"
                    f"User ID: {user_id}\n"
                    f"Username: @{username}\n"
                    f"Amount: {amount} {CURRENCY} 💸\n"
                    f"Payment Method: **{context.user_data.get('payment_method', 'N/A')}**\n"
                    f"Details: {context.user_data.get('withdrawal_details', 'N/A')}\n"
                    f"Invited Users: {user.get('invited_users', 0)}\n"
                    f"Status: Rejected ❌"
                )
                try:
                    await context.bot.edit_message_text(
                        chat_id=LOG_CHANNEL_ID,
                        message_id=message_id,
                        text=updated_message,
                        parse_mode="Markdown"
                    )
                    logger.info(f"Updated log channel message {message_id} to 'Rejected' for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to edit log channel message {message_id} for user {user_id}: {e}")

            logger.info(f"Withdrawal rejected for user {user_id}. Amount: {amount}, Refunded balance: {new_balance}")
            await query.message.reply_text(f"Withdrawal rejected for user {user_id}. Amount: {amount} {CURRENCY}.")
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Your withdrawal request of {amount} {CURRENCY} has been rejected by the admin. The amount has been refunded to your balance. Your new balance is {new_balance} {CURRENCY}. If there are any problems or you wish to appeal, please contact @actanibot.\n"
                         f"သင့်ငွေထုတ်မှု တောင်းဆိုမှု {amount} {CURRENCY} ကို အုပ်ချုပ်ရေးမှူးမှ ပယ်ချလိုက်ပါသည်။ ပမာဏကို သင့်လက်ကျန်သို့ ပြန်လည်ထည့်သွင်းပြီးပါပြီ။ သင့်လက်ကျန်ငွေ အသစ်မှာ {new_balance} {CURRENCY} ဖြစ်ပါသည်။ ပြဿနာများရှိပါက သို့မဟုတ် အယူခံဝင်လိုပါက @actanibot သို့ ဆက်သွယ်ပါ။"
                )
                logger.info(f"Notified user {user_id} of withdrawal rejection")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id} of withdrawal rejection: {e}")

        elif data.startswith("post_approval_"):
            parts = data.split("_")
            if len(parts) != 4:
                logger.error(f"Invalid callback data format: {data}")
                await query.message.reply_text("Error processing approval post.")
                return
            _, _, user_id, amount = parts
            user_id = user_id
            amount = int(amount)

            user = await db.get_user(user_id)
            if not user:
                logger.error(f"User {user_id} not found for approval post")
                await query.message.reply_text("User not found.")
                return

            username = user.get("username", user.get("name", "Unknown"))
            mention = f"@{username}" if username and not username.isdigit() else user["name"]
            group_message = f"{mention} သူက ငွေ {amount} ကျပ်ထုတ်ခဲ့သည် ချိုချဉ်ယ်စားပါ"

            try:
                await context.bot.send_message(
                    chat_id=GROUP_CHAT_IDS[0],
                    text=group_message
                )
                await query.message.reply_text(f"Posted withdrawal announcement to group {GROUP_CHAT_IDS[0]}.")
                logger.info(f"Sent withdrawal announcement to group {GROUP_CHAT_IDS[0]} for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send group announcement for user {user_id}: {e}")
                await query.message.reply_text("Failed to post to group. Please try again.")

    except Exception as e:
        logger.error(f"Error in handle_admin_receipt: {e}")
        await query.message.reply_text("Error processing withdrawal request. Please try again.")

# Cancel the withdrawal process
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"User {user_id} canceled the withdrawal process")

    # Refund any deducted amount if the user cancels
    user = await db.get_user(user_id)
    pending_withdrawals = user.get("pending_withdrawals", [])
    if pending_withdrawals:
        amount = pending_withdrawals[0]["amount"]
        balance = user.get("balance", 0)
        new_balance = balance + amount
        await db.update_user(user_id, {
            "balance": new_balance,
            "pending_withdrawals": []
        })
        logger.info(f"Refunded {amount} to user {user_id} on cancellation. New balance: {new_balance}")
        await update.message.reply_text(
            f"Withdrawal canceled. The amount has been refunded to your balance. Your new balance is {new_balance} {CURRENCY}.\n"
            f"ငွေထုတ်မှု ပယ်ဖျက်လိုက်ပါသည်။ ပမာဏကို သင့်လက်ကျန်သို့ ပြန်လည်ထည့်သွင်းပြီးပါပြီ။ သင့်လက်ကျန်ငွေ အသစ်မှာ {new_balance} {CURRENCY} ဖြစ်ပါသည်။"
        )
    else:
        await update.message.reply_text("Withdrawal canceled.\nငွေထုတ်မှု ပယ်ဖျက်လိုက်ပါသည်။")

    context.user_data.clear()
    return ConversationHandler.END

def register_handlers(application: Application):
    logger.info("Registering withdrawal handlers")
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("withdraw", withdraw),
            CallbackQueryHandler(withdraw, pattern="^start_withdraw$"),
        ],
        states={
            STEP_PAYMENT_METHOD: [CallbackQueryHandler(handle_payment_method_selection, pattern="^payment_")],
            STEP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
            STEP_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_details)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex("^(Cancel|cancel)$"), cancel),
        ],
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_admin_receipt, pattern="^(approve_withdrawal_|reject_withdrawal_|post_approval_)"))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CallbackQueryHandler(balance, pattern="^check_balance$"))