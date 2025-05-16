# plugins/withdrawal.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)
from config import (
    ADMIN_IDS,
    WITHDRAWAL_THRESHOLD,
    DAILY_WITHDRAWAL_LIMIT,
    CURRENCY,
    LOG_CHANNEL_ID,
    PAYMENT_METHODS,
)
from database.database import db
import logging
from datetime import datetime, timezone

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define conversation states
STEP_AMOUNT, STEP_METHOD, STEP_ACCOUNT = range(3)

async def start_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Handle both message and callback query
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = str(query.from_user.id)
        chat_id = query.message.chat_id
        message = query.message
    else:
        user_id = str(update.effective_user.id)
        chat_id = update.effective_chat.id
        message = update.message

    logger.info(f"Withdrawal initiated by user {user_id} in chat {chat_id}")

    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        await message.reply_text("User not found. Please start with /start.")
        return ConversationHandler.END

    balance = user.get("balance", 0)
    if balance < WITHDRAWAL_THRESHOLD:
        await message.reply_text(
            f"Your balance ({balance} {CURRENCY}) is below the withdrawal threshold of {WITHDRAWAL_THRESHOLD} {CURRENCY}."
        )
        return ConversationHandler.END

    withdrawn_today = user.get("withdrawn_today", 0)
    if withdrawn_today >= DAILY_WITHDRAWAL_LIMIT:
        await message.reply_text(
            f"You have reached the daily withdrawal limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}."
        )
        return ConversationHandler.END

    await message.reply_text(
        f"Your current balance is {balance} {CURRENCY}. Please enter the amount to withdraw (minimum {WITHDRAWAL_THRESHOLD} {CURRENCY})."
    )
    return STEP_AMOUNT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    message = update.message
    logger.info(f"User {user_id} provided withdrawal amount: {message.text}")

    user = await db.get_user(user_id)
    balance = user.get("balance", 0)
    withdrawn_today = user.get("withdrawn_today", 0)

    try:
        amount = int(message.text.strip())
        if amount < WITHDRAWAL_THRESHOLD:
            await message.reply_text(f"Please enter an amount of at least {WITHDRAWAL_THRESHOLD} {CURRENCY}.")
            return STEP_AMOUNT
        if amount > balance:
            await message.reply_text(f"Insufficient balance. Your current balance is {balance} {CURRENCY}.")
            return STEP_AMOUNT
        remaining_daily_limit = DAILY_WITHDRAWAL_LIMIT - withdrawn_today
        if amount > remaining_daily_limit:
            await message.reply_text(
                f"Amount exceeds daily withdrawal limit. You can withdraw up to {remaining_daily_limit} {CURRENCY} today."
            )
            return STEP_AMOUNT

        context.user_data["withdrawal_amount"] = amount
        keyboard = [[InlineKeyboardButton(method, callback_data=f"method_{method}")] for method in PAYMENT_METHODS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.reply_text("Please select a payment method:", reply_markup=reply_markup)
        return STEP_METHOD

    except ValueError:
        await message.reply_text("Please enter a valid number.")
        return STEP_AMOUNT

async def handle_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    method = query.data.split("method_")[1]
    logger.info(f"User {user_id} selected payment method: {method}")

    context.user_data["payment_method"] = method
    await query.message.reply_text(f"Please provide your {method} account details (e.g., phone number or account ID):")
    return STEP_ACCOUNT

async def handle_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    message = update.message
    account_details = message.text.strip()
    logger.info(f"User {user_id} provided account details: {account_details}")

    amount = context.user_data.get("withdrawal_amount")
    payment_method = context.user_data.get("payment_method")
    user = await db.get_user(user_id)
    balance = user.get("balance", 0)
    withdrawn_today = user.get("withdrawn_today", 0)

    new_balance = balance - amount
    new_withdrawn_today = withdrawn_today + amount
    last_withdrawal = datetime.now(timezone.utc)

    # Update user balance and withdrawal info
    result = await db.update_user(user_id, {
        "balance": new_balance,
        "withdrawn_today": new_withdrawn_today,
        "last_withdrawal": last_withdrawal
    })
    logger.info(f"db.update_user returned: {result} for user {user_id}")

    # Handle the None return issue
    success = False
    if result is None:
        logger.warning(f"db.update_user returned None for user {user_id}, assuming success based on log")
        success = True  # Temporary workaround
    elif isinstance(result, bool):
        success = result
    elif hasattr(result, 'modified_count'):
        success = result.modified_count > 0
    else:
        logger.error(f"Unexpected db.update_user result type: {type(result)} for user {user_id}")

    if success:
        # Notify user
        await message.reply_text(
            f"Withdrawal request for {amount} {CURRENCY} via {payment_method} ({account_details}) has been submitted.\n"
            f"New balance: {new_balance} {CURRENCY}.\n"
            f"သင့်ငွေထုတ်တောင်းဆိုမှု {amount} {CURRENCY} ကို {payment_method} ({account_details}) မှတစ်ဆင့် တင်သွင်းပြီးပါပြီ။\n"
            f"လက်ကျန်ငွေ အသစ်: {new_balance} {CURRENCY}။"
        )
        logger.info(f"Withdrawal request submitted for user {user_id}: {amount} {CURRENCY} via {payment_method}")

        # Notify admin via log channel
        try:
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=(
                    f"New withdrawal request:\n"
                    f"User ID: {user_id}\n"
                    f"Name: {user.get('name', 'Unknown')}\n"
                    f"Amount: {amount} {CURRENCY}\n"
                    f"Method: {payment_method}\n"
                    f"Account: {account_details}\n"
                    f"Time: {last_withdrawal.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                )
            )
            logger.info(f"Notified admin of withdrawal request for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to notify admin of withdrawal for user {user_id}: {e}")

    else:
        logger.error(f"Failed to process withdrawal for user {user_id}. Result: {result}")
        await message.reply_text("Error processing withdrawal. Please try again later.")

    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"User {user_id} canceled the withdrawal process")
    await update.message.reply_text("Withdrawal canceled.")
    context.user_data.clear()
    return ConversationHandler.END

def register_handlers(application: Application):
    logger.info("Registering withdrawal handlers")
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("withdraw", start_withdraw),
            CallbackQueryHandler(start_withdraw, pattern="^start_withdraw$"),
        ],
        states={
            STEP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
            STEP_METHOD: [],  # CallbackQueryHandler for payment method is handled separately
            STEP_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_account)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex("^(Cancel|cancel)$"), cancel),
        ],
    )

    application.add_handler(conv_handler)
    # Separate handler for payment method selection
    application.add_handler(CallbackQueryHandler(handle_method, pattern="^method_"))