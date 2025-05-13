from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)
from config import GROUP_CHAT_ID, WITHDRAWAL_THRESHOLD, DAILY_WITHDRAWAL_LIMIT, CURRENCY, LOG_CHANNEL_ID
from database.database import db
import logging
from datetime import datetime, timezone

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define withdrawal steps
STEP_AMOUNT = 0

# Entry point for /withdraw command
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    logger.info(f"Withdraw function called for user {user_id} in chat {chat_id}")

    # Ensure this is a private chat
    if update.effective_chat.type != "private":
        logger.info(f"User {user_id} attempted withdrawal in non-private chat {chat_id}")
        await update.message.reply_text("Please use the /withdraw command in a private chat.")
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

        # For now, simulate processing (expand with payment steps later)
        await message.reply_text(
            f"You entered: {amount} {CURRENCY}. Withdrawal request submitted! (Processing simulated)\n"
            f"သင်ထည့်ထားသော ပမာဏ - {amount} {CURRENCY}။ ငွေထုတ်မှု တင်ပြခဲ့ပါသည်။ (လုပ်ဆောင်မှု နောက်မှ ထည့်မည်)"
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

# Register handlers for the application
def register_handlers(application: Application):
    logger.info("Registering withdrawal handlers")
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("withdraw", withdraw)],
        states={
            STEP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)