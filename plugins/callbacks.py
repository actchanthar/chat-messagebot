# plugins/callbacks.py
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
import logging
from database.database import db
from config import LOG_CHANNEL_ID, WITHDRAWAL_THRESHOLD

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user = await db.get_user(user_id)
    balance = user.get("balance", 0) if user else 0
    await query.edit_message_text(f"Your balance: {balance} kyat")

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user = await db.get_user(user_id)
    balance = user.get("balance", 0) if user else 0

    if balance < WITHDRAWAL_THRESHOLD:  # Use WITHDRAWAL_THRESHOLD from config.py (100 kyat)
        await query.edit_message_text(
            f"Your balance is {balance} kyat. "
            f"Minimum withdrawal amount is {WITHDRAWAL_THRESHOLD} kyat. Earn more to withdraw!"
        )
        return

    # Notify admin in LOG_CHANNEL_ID
    try:
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=(
                f"💸 Withdrawal Request\n"
                f"User ID: {user_id}\n"
                f"Username: @{query.from_user.username or 'N/A'}\n"
                f"Name: {user.get('name', 'Unknown')}\n"
                f"Balance: {balance} kyat\n"
                f"Please process the withdrawal."
            )
        )
        logger.info(f"Withdrawal request sent to admin for user {user_id} with balance {balance}")
    except Exception as e:
        logger.error(f"Failed to notify admin for withdrawal request by user {user_id}: {e}")

    # Respond to user with admin contact info
    await query.edit_message_text(
        f"Your withdrawal request for {balance} kyat has been submitted!\n"
        "Please wait for the admin to process it.\n"
        "Contact Admin: @When_the_night_falls_my_soul_se\n"
        "Support Chat: https://t.me/stranger77777777777"
    )

def register_handlers(application: Application):
    logger.info("Registering callback handlers")
    application.add_handler(CallbackQueryHandler(balance_callback, pattern="^balance$"))
    application.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^withdraw$"))