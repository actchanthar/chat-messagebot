from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    logger.info(f"Balance check initiated by user {user_id} via button")

    user = await db.get_user(user_id)
    if not user:
        await query.message.reply_text("User not found. Please start with /start.")
        logger.error(f"User {user_id} not found in database")
        return

    balance = user.get("balance", 0)
    await query.message.reply_text(
        f"Your current balance is {balance} kyat.\nသင့်လက်ကျန်ငွေသည် {balance} ကျပ်ဖြစ်ပါသည်။",
        reply_markup=query.message.reply_markup  # Preserve the original keyboard
    )
    logger.info(f"Sent balance {balance} to user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering balance handlers")
    application.add_handler(CallbackQueryHandler(check_balance, pattern="^balance$"))