from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(update.effective_user.id if not query else query.from_user.id)
    logger.info(f"Balance check initiated by user {user_id} via {'button' if query else 'command'}")

    user = await db.get_user(user_id)
    if not user:
        await (query.message if query else update.message).reply_text("User not found. Please start with /start.")
        logger.error(f"User {user_id} not found in database")
        return

    balance = user.get("balance", 0)
    balance_rounded = int(balance)  # Round to whole number
    reply_text = (
        f"Your current balance is {balance_rounded} kyat.\n"
        f"သင့်လက်ကျန်ငွေသည် {balance_rounded} ကျပ်ဖြစ်ပါသည်။"
    )
    await (query.message if query else update.message).reply_text(reply_text, reply_markup=query.message.reply_markup if query else None)
    logger.info(f"Sent balance {balance_rounded} to user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering balance handlers")
    application.add_handler(CallbackQueryHandler(check_balance, pattern="^balance$"))
    application.add_handler(CommandHandler("balance", check_balance))