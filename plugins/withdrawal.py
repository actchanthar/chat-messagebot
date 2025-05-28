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

# Define conversation states
STEP_PAYMENT_METHOD, STEP_AMOUNT, STEP_DETAILS = range(3)

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Withdraw command initiated by user {user_id} in chat {chat_id}")

    # Ensure the command is used in a private chat
    if update.effective_chat.type != "private":
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text("Please use /withdraw in a private chat.")
        else:
            await update.message.reply_text("Please use /withdraw in a private chat.")
        logger.info(f"User {user_id} attempted withdrawal in non-private chat {chat_id}")
        return ConversationHandler.END

    # Fetch user from the database
    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text("User not found. Please start with /start.")
        else:
            await update.message.reply_text("User not found. Please start with /start.")
        return ConversationHandler.END

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text("You are banned from using this bot.")
        else:
            await update.message.reply_text("You are banned from using this bot.")
        return ConversationHandler.END

    # Clear any existing conversation data
    context.user_data.clear()
    logger.info(f"Cleared user_data for user {user_id}")

    # Prompt for payment method selection
    keyboard = [[InlineKeyboardButton(method, callback_data=f"method_{method}")] for method in PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "Please select a payment method: 💳\n"
            "ကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။",
            reply_markup=reply_markup
        )
        await update.callback_query.message.delete()  # Optional: Clean up the start message
    else:
        await update.message.reply_text(
            "Please select a payment method: 💳\n"
            "ကျေးဇူးပြု၍ ငွေပေးချေမှုနည်းလမ်းကို ရွေးချယ်ပါ။",
            reply_markup=reply_markup
        )
    logger.info(f"Prompted user {user_id} for payment method selection")
    return STEP_PAYMENT_METHOD

async def handle_withdraw_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the 'withdraw' callback from the start message."""
    user_id = str(update.effective_user.id)
    logger.info(f"Withdraw button clicked by user {user_id}")
    return await withdraw(update, context)  # Reuse the withdraw function

async def handle_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = query.data
    logger.info(f"Payment method selection for user {user_id}, data: {data}")

    if not data.startswith("method_"):
        logger.error(f"Invalid callback data for user {user_id}: {data}")
        await query.message.reply_text("Invalid selection. Please start again with /withdraw.")
        return ConversationHandler.END

    method = data.replace("method_", "")
    if method not in PAYMENT_METHODS:
        logger.error(f"Invalid payment method {method} for user {user_id}")
        await query.message.reply_text("Invalid payment method. Please try again.")
        return STEP_PAYMENT_METHOD

    context.user_data["payment_method"] = method
    logger.info(f"User {user_id} selected payment method: {method}")

    # For Phone Bill, set a fixed amount and skip to details
    if method == "Phone Bill":
        context.user_data["withdrawal_amount"] = 1000
        await query.message.reply_text(
            "Phone Bill withdrawals are fixed at 1000 kyat.\n"
            "Please send your phone number (e.g., 09123456789)."
        )
        return STEP_DETAILS

    # Otherwise, ask for the amount
    await query.message.reply_text(
        f"Please enter the amount to withdraw (minimum: {WITHDRAWAL_THRESHOLD} {CURRENCY}).\n"
        f"ငွေထုတ်ရန် ပမာဏကို ထည့်ပါ (အနည်းဆုံး {WITHDRAWAL_THRESHOLD} {CURRENCY})"
    )
    return STEP_AMOUNT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    message = update.message
    logger.info(f"Received amount input from user {user_id}: {message.text}")

    # Verify payment method is set
    payment_method = context.user_data.get("payment_method")
    if not payment_method:
        logger.error(f"No payment method in context for user {user_id}")
        await message.reply_text("Error: Payment method missing. Please start again with /withdraw.")
        return ConversationHandler.END

    try:
        amount = int(message.text.strip())
        logger.info(f"Parsed amount for user {user_id}: {amount}")

        # Check minimum withdrawal amount
        if amount < WITHDRAWAL_THRESHOLD:
            await message.reply_text(
                f"Minimum withdrawal is {WITHDRAWAL_THRESHOLD} {CURRENCY}. Please try again."
            )
            return STEP_AMOUNT

        # Fetch user data
        user = await db.get_user(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            await message.reply_text("User not found. Please start with /start.")
            return ConversationHandler.END

        # Check balance
        balance = user.get("balance", 0)
        if balance < amount:
            logger.info(f"Insufficient balance for user {user_id}: {balance} < {amount}")
            await message.reply_text(
                f"Insufficient balance. Your balance is {balance} {CURRENCY}. Use /balance to check."
            )
            return ConversationHandler.END

        # Check daily withdrawal limit
        last_withdrawal = user.get("last_withdrawal")
        withdrawn_today = user.get("withdrawn_today", 0)
        current_time = datetime.now(timezone.utc)
        if last_withdrawal and last_withdrawal.date() == current_time.date():
            if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                logger.info(f"Daily limit exceeded for user {user_id}: {withdrawn_today} + {amount} > {DAILY_WITHDRAWAL_LIMIT}")
                await message.reply_text(
                    f"Daily limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY} exceeded. Withdrawn today: {withdrawn_today} {CURRENCY}."
                )
                return STEP_AMOUNT

        # Store the amount and proceed to details
        context.user_data["withdrawal_amount"] = amount
        logger.info(f"Stored withdrawal amount {amount} for user {user_id}")

        # Prompt for payment details based on method
        if payment_method == "KBZ Pay":
            await message.reply_text(
                "Please provide your KBZ Pay details (e.g., 09123456789 NAME) or upload a QR image.\n"
                "သင့် KBZ Pay အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789 နာမည်) သို့မဟုတ် QR ပုံကို တင်ပါ။"
            )
        elif payment_method == "Wave Pay":
            await message.reply_text(
                "Please provide your Wave Pay details (e.g., 09123456789 NAME) or upload a QR image.\n"
                "သင့် Wave Pay အသေးစိတ်ကို ပေးပါ (ဥပမာ 09123456789 နာမည်) သို့မဟုတ် QR ပုံကို တင်ပါ။"
            )
        else:  # Phone Bill
            await message.reply_text(
                "Please send your phone number (e.g., 09123456789)."
            )

        logger.info(f"Prompted user {user_id} for payment details (method: {payment_method})")
        return STEP_DETAILS

    except ValueError:
        logger.warning(f"Invalid amount format from user {user_id}: {message.text}")
        await message.reply_text("Please enter a valid number (e.g., 100).")
        return STEP_AMOUNT
    except Exception as e:
        logger.error(f"Error processing amount for user {user_id}: {e}")
        await message.reply_text("An error occurred. Please try again with /withdraw.")
        return ConversationHandler.END

async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"Received payment details from user {user_id}")

    # Verify required data
    amount = context.user_data.get("withdrawal_amount")
    payment_method = context.user_data.get("payment_method")
    if not amount or not payment_method:
        logger.error(f"Missing amount or method for user {user_id}: {context.user_data}")
        await update.message.reply_text("Error: Invalid withdrawal data. Please start again with /withdraw.")
        return ConversationHandler.END

    # Handle photo (QR image) or text input
    details = None
    photo_file_id = None
    if update.message and update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        photo_file_id = photo_file.file_id  # Store file_id for sending
        details = f"QR Image"  # Simplified details text
        logger.info(f"User {user_id} uploaded QR image with file_id: {photo_file_id}")
    elif update.message and update.message.text:
        details = update.message.text.strip() or "No details provided"
        logger.info(f"User {user_id} provided text details: {details}")
    else:
        logger.warning(f"No valid input from user {user_id}")
        await update.message.reply_text("Please provide details or upload a QR image.")
        return STEP_DETAILS

    # Fetch user data
    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found")
        await update.message.reply_text("User not found. Please start with /start.")
        return ConversationHandler.END

    # Store payment details
    context.user_data["withdrawal_details"] = details if not photo_file_id else f"QR Image: {photo_file_id}"
    logger.info(f"Stored payment details for user {user_id}: {context.user_data['withdrawal_details']}")

    # Prepare admin approval message
    keyboard = [
        [InlineKeyboardButton("Approve ✅", callback_data=f"approve_{user_id}_{amount}"),
         InlineKeyboardButton("Reject ❌", callback_data=f"reject_{user_id}_{amount}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    name = user.get("name", "Unknown")
    username = user.get("username", "N/A")
    log_message = (
        f"Withdrawal Request:\n"
        f"User ID: {user_id}\n"
        f"Name: {name}\n"
        f"Username: @{username}\n"
        f"Amount: {amount} {CURRENCY}\n"
        f"Method: {payment_method}\n"
        f"Details: {details if not photo_file_id else 'See attached QR image'}\n"
        f"Status: PENDING ⏳"
    )

    # Send request to admin log channel
    try:
        # Send text message
        log_msg = await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=log_message,
            reply_markup=reply_markup
        )
        # Send QR image if available
        if photo_file_id:
            await context.bot.send_photo(
                chat_id=LOG_CHANNEL_ID,
                photo=photo_file_id,
                caption="Attached QR Image for Withdrawal Request",
                reply_to_message_id=log_msg.message_id
            )
        await context.bot.pin_chat_message(chat_id=LOG_CHANNEL_ID, message_id=log_msg.message_id)
        await db.update_user(user_id, {
            "pending_withdrawals": user.get("pending_withdrawals", []) + [{
                "amount": amount,
                "payment_method": payment_method,
                "details": context.user_data["withdrawal_details"],
                "status": "PENDING",
                "message_id": log_msg.message_id
            }]
        })
        logger.info(f"Withdrawal request submitted to log channel for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to submit withdrawal request for user {user_id}: {e}")
        await update.message.reply_text("Error submitting request. Please try again.")
        return ConversationHandler.END

    # Notify user
    await update.message.reply_text(
        f"Withdrawal request for {amount} {CURRENCY} submitted. Awaiting admin approval. ⏳\n"
        f"သင့်ငွေထုတ်မှု {amount} {CURRENCY} ကို တင်ပြခဲ့ပါသည်။ အက်ဒမင်၏ အတည်ပြုချက်ကို စောင့်ပါ။"
    )
    logger.info(f"Notified user {user_id} of pending withdrawal request")
    return ConversationHandler.END

async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"Admin action received: {data}")

    try:
        if data.startswith("approve_"):
            _, user_id, amount = data.split("_")
            user_id, amount = str(user_id), int(amount)

            user = await db.get_user(user_id)
            if not user:
                logger.error(f"Invalid approval for user {user_id} (user not found)")
                await query.message.reply_text("Error: User not found.")
                return

            balance = user.get("balance", 0)
            if balance < amount:
                logger.error(f"Insufficient balance for user {user_id}: {balance} < {amount}")
                await query.message.reply_text(f"Error: Insufficient balance. Current balance: {balance} {CURRENCY}.")
                return

            # Deduct balance and update withdrawal records atomically
            new_balance = balance - amount
            withdrawn_today = user.get("withdrawn_today", 0)
            current_time = datetime.now(timezone.utc)
            if user.get("last_withdrawal") and user["last_withdrawal"].date() == current_time.date():
                if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
                    logger.error(f"Daily limit exceeded for user {user_id}")
                    await query.message.reply_text(f"Daily limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY} exceeded.")
                    return
                withdrawn_today += amount
            else:
                withdrawn_today = amount

            await db.update_user(user_id, {
                "balance": new_balance,
                "last_withdrawal": current_time,
                "withdrawn_today": withdrawn_today,
                "pending_withdrawals": [w for w in user.get("pending_withdrawals", []) if w["amount"] != amount or w["status"] != "PENDING"]
            })
            logger.info(f"Approved withdrawal of {amount} {CURRENCY} for user {user_id}. New balance: {new_balance}")
            await query.message.reply_text(f"Approved {amount} {CURRENCY} for user {user_id}. New balance: {new_balance} {CURRENCY}.")
            await context.bot.send_message(
                user_id,
                f"Your withdrawal of {amount} {CURRENCY} has been approved. New balance: {new_balance} {CURRENCY}."
            )

        elif data.startswith("reject_"):
            _, user_id, amount = data.split("_")
            user_id, amount = str(user_id), int(amount)

            user = await db.get_user(user_id)
            if user:
                await db.update_user(user_id, {
                    "pending_withdrawals": [w for w in user.get("pending_withdrawals", []) if w["amount"] != amount or w["status"] != "PENDING"]
                })
            logger.info(f"Rejected withdrawal of {amount} {CURRENCY} for user {user_id}")
            await query.message.reply_text(f"Rejected {amount} {CURRENCY} for user {user_id}.")
            await context.bot.send_message(
                user_id,
                f"Your withdrawal of {amount} {CURRENCY} was rejected. Please contact support."
            )

    except Exception as e:
        logger.error(f"Error in admin action for {data}: {e}")
        await query.message.reply_text("Error processing request.")

def register_handlers(application: Application):
    logger.info("Registering withdrawal handlers")
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("withdraw", withdraw),
            CallbackQueryHandler(handle_withdraw_button, pattern="^withdraw$")  # Handle button click
        ],
        states={
            STEP_PAYMENT_METHOD: [CallbackQueryHandler(handle_payment_method, pattern="^method_")],
            STEP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
            STEP_DETAILS: [MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_details)],
        },
        fallbacks=[CommandHandler("withdraw", withdraw)],
        conversation_timeout=300,  # 5 minutes timeout
        per_message=False  # Prevents tracking every message
    )
    application.add_handler(conv_handler, group=1)  # Higher group number for priority
    application.add_handler(CallbackQueryHandler(handle_admin_action, pattern="^(approve_|reject_)"), group=1)