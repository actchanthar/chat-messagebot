from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from database.database import db
import logging
from config import WITHDRAWAL_THRESHOLD, DAILY_WITHDRAWAL_LIMIT, PAYMENT_METHODS, ADMIN_IDS, LOG_CHANNEL_ID, CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Withdraw request by user {user_id} in chat {chat_id}")

    user = await db.get_user(user_id)
    if not user:
        logger.info(f"User {user_id} not found")
        await update.message.reply_text("User not found. Please start the bot with /start.")
        return

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        await update.message.reply_text("You are banned from withdrawing.")
        return

    balance = user.get("balance", 0)
    if balance < WITHDRAWAL_THRESHOLD:
        logger.info(f"User {user_id} balance {balance} below threshold {WITHDRAWAL_THRESHOLD}")
        await update.message.reply_text(f"Your balance ({balance} {CURRENCY}) is below the minimum withdrawal threshold ({WITHDRAWAL_THRESHOLD} {CURRENCY}).")
        return

    today_withdrawn = user.get("today_withdrawn", 0)
    if today_withdrawn >= DAILY_WITHDRAWAL_LIMIT:
        logger.info(f"User {user_id} exceeded daily withdrawal limit")
        await update.message.reply_text(f"You have reached the daily withdrawal limit of {DAILY_WITHDRAWAL_LIMIT} {CURRENCY}.")
        return

    invite_count = len(user.get("invited_users", []))  # Count invited users
    invite_requirement = 0 if user_id in ADMIN_IDS else await db.get_invite_requirement()  # 3 for non-admins

    if invite_count < invite_requirement:
        logger.info(f"User {user_id} has {invite_count} invites, needs {invite_requirement}")
        await update.message.reply_text(f"You need to invite at least {invite_requirement} users to withdraw. Current invites: {invite_count}.")
        return

    keyboard = [[InlineKeyboardButton(method, callback_data=f"withdraw_{method}")] for method in PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a payment method:", reply_markup=reply_markup)
    logger.info(f"Prompted user {user_id} to select payment method")

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    chat_id = str(query.message.chat.id)
    method = query.data.split("_")[1]
    logger.info(f"Withdraw callback for user {user_id} with method {method}")

    user = await db.get_user(user_id)
    if not user:
        logger.info(f"User {user_id} not found")
        await query.message.reply_text("User not found.")
        return

    balance = user.get("balance", 0)
    today_withdrawn = user.get("today_withdrawn", 0)
    available = min(balance, DAILY_WITHDRAWAL_LIMIT - today_withdrawn)

    if available < WITHDRAWAL_THRESHOLD:
        logger.info(f"User {user_id} available balance {available} below threshold")
        await query.message.reply_text(f"Available balance ({available} {CURRENCY}) is below the minimum withdrawal threshold ({WITHDRAWAL_THRESHOLD} {CURRENCY}).")
        return

    payment_number = user.get("payment_number")
    if not payment_number:
        logger.info(f"User {user_id} has no payment number")
        await query.message.reply_text("Please set your payment number using /setphonebill.")
        return

    try:
        await db.update_user(user_id, {
            "balance": balance - available,
            "today_withdrawn": today_withdrawn + available
        })
        await db.add_withdrawal(user_id, available, method, payment_number)
        logger.info(f"Processed withdrawal for user {user_id}: {available} {CURRENCY} via {method}")

        await query.message.reply_text(
            f"Withdrawal request for {available} {CURRENCY} via {method} has been submitted.\n"
            f"Payment Number: {payment_number}\n"
            "You will be notified once processed."
        )

        admin_message = (
            f"New Withdrawal Request\n"
            f"User ID: {user_id}\n"
            f"Amount: {available} {CURRENCY}\n"
            f"Method: {method}\n"
            f"Payment Number: {payment_number}"
        )
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=admin_message)
    except Exception as e:
        logger.error(f"Error processing withdrawal for {user_id}: {str(e)}")
        await query.message.reply_text("Error processing withdrawal. Please try again.")

def register_handlers(application: Application):
    logger.info("Registering withdrawal handlers")
    application.add_handler(CommandHandler("withdraw", withdraw))
    application.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^withdraw_"))