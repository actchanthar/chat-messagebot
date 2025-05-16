# plugins/callbacks.py (example)
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
import logging
from database.database import db

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
    if balance < 100:  # Assuming minimum withdrawal threshold from config.py
        await query.edit_message_text("Minimum withdrawal amount is 100 kyat. Earn more to withdraw!")
    else:
        await query.edit_message_text("Please contact admin to process your withdrawal.")
        logger.info(f"Withdrawal requested by user {user_id} with balance {balance}")

def register_handlers(application: Application):
    logger.info("Registering callback handlers")
    application.add_handler(CallbackQueryHandler(balance_callback, pattern="^balance$"))
    application.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^withdraw$"))