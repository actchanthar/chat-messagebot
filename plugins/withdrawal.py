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
from config import GROUP_CHAT_IDS, WITHDRAWAL_THRESHOLD, DAILY_WITHDRAWAL_LIMIT, CURRENCY, LOG_CHANNEL_ID, PAYMENT_METHODS  # Updated to use GROUP_CHAT_IDS
from database.database import db
import logging
from datetime import datetime, timezone

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define withdrawal steps
STEP_PAYMENT_METHOD, STEP_AMOUNT, STEP_DETAILS = range(3)

# Entry point for /withdraw command and button callback
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    source = "command" if update.message else "button"
    logger.info(f"Withdraw function called for user {user_id} in chat {chat_id} via {source}")

    # If triggered by a button, answer the callback query
    if update.callback_query:
        await update.callback_query.answer()

    # Ensure this is a private chat
    if update.effective_chat.type != "private":
        logger.info(f"User {user_id} attempted withdrawal in non-private chat {chat_id}")
        if update.message:
            await update.message.reply_text("Please use the /withdraw command in a private chat.")
        else:
            await update.callback_query.message.reply_text("Please use /withdraw in a private chat.")
        return ConversationHandler.END

    user = await db.get_user(str(user_id))
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

    # Clear any existing conversation data to start fresh
    context.user_data.clear()
    logger.info(f"Cleared user_data for user {user_id} before starting withdrawal process")

    # Show payment method selection buttons first
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
    user_id = update.effective_user.id
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

    # If Phone Bill is selected, set amount to 1000 and skip amount input
    if method == "Phone Bill":
        context.user_data["withdrawal_amount"] = 1000
        await query.message.reply_text(
            "Phone Bill withdrawals are fixed at 1000 kyat for top-up.\n"
            "Please provide your phone number for Phone Bill payment. 💳\n"
            "ကျေးဇူးပြု၍ ဖုန်းဘေလ်ငွေပေးချေမှုအတွက် သင့်ဖုန်းနံပါတ်ကို ပေးပါ။"
        )
        logger.info(f"User {user_id} selected Phone Bill, fixed amount to 1000 kyat")
        return STEP_DETAILS

    # For other methods, prompt for amount
    await query.message.reply_text(
        f"Please enter the amount you wish to withdraw (minimum: {WITHDRAWAL_THRESHOLD} {CURRENCY}). 💸\n"
        f"ငွေထုတ်ရန် ပမာဏကိုရေးပို့ပါ အနည်းဆုံး {WITHDRAWAL_THRESHOLD} ပြည့်မှထုတ်လို့ရမှာပါ"
    )
    return STEP_AMOUNT

# Handle withdrawal amount input
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
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

        user = await db.get_user(str(user_id))
        if not user:
            await message.reply_text("User not found. Please start again with /start.")
            return ConversationHandler.END

        # Check daily withdrawal limit here and show to user
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

        if user.get("balance", 0) < amount:
            await message.reply_text("Insufficient balance. Please check your balance with /balance.")
            return ConversationHandler.END

        # Store amount in context
        context.user_data["withdrawal_amount"] = amount
        context.user_data["withdrawn_today"] = withdrawn_today
        logger.info(f"Stored withdrawal amount {amount} for user {user_id}, context: {context.user_data}")

        # Prompt for payment details based on method
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
    user_id = update.effective_user.id
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

    user = await db.get_user(str(user_id))
    if not user:
        logger.error(f"User {user_id} not found in database")
        await message.reply_text("User not found. Please start again with /start.")
        return ConversationHandler.END

    payment_details = message.text if message.text else "No details provided"
    context.user_data["withdrawal_details"] = payment_details
    logger.info(f"User {user_id} submitted account details, context: {context.user_data}")

    # Send withdrawal request to admin log channel
    keyboard = [
        [
            InlineKeyboardButton("Approve ✅", callback_data=f"approve_withdrawal_{user_id}_{amount}"),
            InlineKeyboardButton("Reject ❌", callback_data=f"reject_withdrawal_{user_id}_{amount}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Format the log message with correct username and specified fields
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
        f"Status: PENDING ⏳"
    )

    try:
        log_msg = await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=log_message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        # Pin the message in the log channel
        await context.bot.pin_chat_message(
            chat_id=LOG_CHANNEL_ID,
            message_id=log_msg.message_id,
            disable_notification=True
        )
        logger.info(f"Sent and pinned withdrawal request to log channel {LOG_CHANNEL_ID} for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send or pin withdrawal request to log channel {LOG_CHANNEL_ID} for user {user_id}: {e}")
        await message.reply_text("Error submitting request. Please try again later.")
        return ConversationHandler.END

    await message.reply_text(
        f"Your withdrawal request for {amount} {CURRENCY} has been submitted. Please wait for admin approval. ⏳\n"
        f"သင့်ငွေထုတ်မှု တောင်းဆိုမှု {amount} {CURRENCY} ကို တင်ပြခဲ့ပါသည်။ ကျေးဇူးပြု၍ အုပ်ချုပ်ရေးမှူး၏ အတည်ပြုချက်ကို စောင့်ပါ။"
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
            user_id = int(user_id)
            amount = int(amount)

            user = await db.get_user(str(user_id))
            if not user:
                logger.error(f"User {user_id} not found for withdrawal approval")
                await query.message.reply_text("User not found.")
                return

            balance = user.get("balance", 0)
            if amount > balance:
                logger.error(f"Insufficient balance for user {user_id}. Requested: {amount}, Balance: {balance}")
                await query.message.reply_text("User has insufficient balance for this withdrawal.")
                return

            last_withdrawal = user.get("last_withdrawal")
            withdrawn_today = user.get("withdrawn_today", 0)
            current_time = datetime.now(timezone.utc)

            if last_withdrawal:
                last_withdrawal_date = last_withdrawal.date()
                current_date = current_time.date()
                if last_withdrawal_date == current_date:
                    if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                        logger.error(f"User {user_id} exceeded daily withdrawal limit. Withdrawn today: {withdrawn_today}, Requested: {amount}")
                        await query.message.reply_text(f"User has exceeded the daily