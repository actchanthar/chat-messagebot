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
from config import GROUP_CHAT_ID, WITHDRAWAL_THRESHOLD, DAILY_WITHDRAWAL_LIMIT, CURRENCY, LOG_CHANNEL_ID
from database.database import db
import logging
from datetime import datetime, timezone

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define withdrawal steps
STEP_AMOUNT = 0

# Entry point for /withdraw command and button callback
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    logger.info(f"Withdraw function called for user {user_id} in chat {chat_id} via {update.message or update.callback_query}")

    # Ensure this is a private chat
    if update.effective_chat.type != "private":
        logger.info(f"User {user_id} attempted withdrawal in non-private chat {chat_id}")
        if update.message:
            await update.message.reply_text("Please use the /withdraw command in a private chat.")
        else:
            await update.callback_query.message.reply_text("Please use /withdraw in a private chat.")
        return ConversationHandler.END

    logger.info(f"Prompting user {user_id} for withdrawal amount in chat {chat_id}")
    await update.message.reply_text(
        f"Please enter the amount you wish to withdraw (minimum: {WITHDRAWAL_THRESHOLD} {CURRENCY}). 💸\n"
        f"ငွေထုတ်ရန် ပမာဏကိုရေးပို့ပါ အနည်းဆုံး {WITHDRAWAL_THRESHOLD} ပြည့်မှထုတ်လို့ရမှာပါ"
    )
    return STEP_AMOUNT

# Handle withdrawal amount input
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message = update.message
    logger.info(f"Received message for amount input from user {user_id} in chat {chat_id}: {message.text}")

    try:
        amount = int(message.text.strip())
        if amount < WITHDRAWAL_THRESHOLD:
            await message.reply_text(
                f"Minimum withdrawal amount is {WITHDRAWAL_THRESHOLD} {CURRENCY}. Please try again.\n"
                f"အနည်းဆုံး {WITHDRAWAL_THRESHOLD} {CURRENCY} ထုတ်နိုင်ပါသည်။ ထပ်စမ်းကြည့်ပါ။"
            )
            return STEP_AMOUNT

        user = await db.get_user(str(user_id))
        if not user or user.get("balance", 0) < amount:
            await message.reply_text("Insufficient balance or user not found. Please check your balance with /balance.")
            return ConversationHandler.END

        # Send withdrawal request to admin log channel
        keyboard = [
            [
                InlineKeyboardButton("Approve ✅", callback_data=f"approve_withdrawal_{user_id}_{amount}"),
                InlineKeyboardButton("Reject ❌", callback_data=f"reject_withdrawal_{user_id}_{amount}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=(
                    f"Withdrawal Request:\n"
                    f"User ID: {user_id}\n"
                    f"User: @{update.effective_user.username or 'N/A'}\n"
                    f"Amount: {amount} {CURRENCY} 💸\n"
                    f"Status: PENDING ⏳"
                ),
                reply_markup=reply_markup
            )
            logger.info(f"Sent withdrawal request to log channel {LOG_CHANNEL_ID} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send withdrawal request to log channel {LOG_CHANNEL_ID} for user {user_id}: {e}")
            await message.reply_text("Error submitting request. Please try again later.")

        await message.reply_text(
            f"You entered: {amount} {CURRENCY}. Withdrawal request submitted! ⏳\n"
            f"သင်ထည့်ထားသော ပမာဏ - {amount} {CURRENCY}။ ငွေထုတ်မှု တင်ပြခဲ့ပါသည်။"
        )
        return ConversationHandler.END

    except ValueError:
        await message.reply_text(
            "Please enter a valid number (e.g., 100).\n"
            "ကျေးဇူးပြု၍ မှန်ကန်သော နံပါတ်ထည့်ပါ (ဥပမာ 100)။"
        )
        return STEP_AMOUNT

# Cancel the withdrawal process
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    logger.info(f"User {user_id} canceled the withdrawal process")
    await update.message.reply_text("Withdrawal canceled.\nငွေထုတ်မှု ပယ်ဖျက်လိုက်ပါသည်။")
    return ConversationHandler.END

# Handle admin approval/rejection (basic implementation)
async def handle_admin_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"Admin receipt callback for user {query.from_user.id}, data: {data}")

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
        if not user or user.get("balance", 0) < amount:
            logger.error(f"Insufficient balance or user {user_id} not found for approval")
            await query.message.reply_text("Insufficient balance or user not found.")
            return

        new_balance = user.get("balance", 0) - amount
        success = await db.update_user(str(user_id), {"balance": new_balance})
        if success:
            logger.info(f"Withdrawal approved for user {user_id}. Amount: {amount}, New balance: {new_balance}")
            await query.message.reply_text(f"Withdrawal approved for user {user_id}. Amount: {amount} {CURRENCY}. New balance: {new_balance} {CURRENCY}.")
            await context.bot.send_message(chat_id=user_id, text=f"Your withdrawal of {amount} {CURRENCY} is approved! New balance: {new_balance} {CURRENCY}.")
        else:
            logger.error(f"Failed to update user {user_id} for withdrawal approval")
            await query.message.reply_text("Error approving withdrawal.")

    elif data.startswith("reject_withdrawal_"):
        parts = data.split("_")
        if len(parts) != 4:
            logger.error(f"Invalid callback data format: {data}")
            await query.message.reply_text("Error processing withdrawal request.")
            return
        _, _, user_id, amount = parts
        user_id = int(user_id)
        amount = int(amount)

        logger.info(f"Withdrawal rejected for user {user_id}. Amount: {amount}")
        await query.message.reply_text(f"Withdrawal rejected for user {user_id}. Amount: {amount} {CURRENCY}.")
        await context.bot.send_message(chat_id=user_id, text=f"Your withdrawal request of {amount} {CURRENCY} was rejected.")

# Register handlers for the application
def register_handlers(application: Application):
    logger.info("Registering withdrawal handlers")
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("withdraw", withdraw),
            CallbackQueryHandler(withdraw, pattern="^withdraw$"),  # Handle button click
        ],
        states={
            STEP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_admin_receipt, pattern="^(approve|reject)_withdrawal_"))