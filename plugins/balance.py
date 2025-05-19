from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(update.effective_user.id if not query else query.from_user.id)
    message = update.message if not query else query.message

    if query:
        await query.answer()

    user = await db.get_user(user_id)
    if not user:
        await message.reply_text("User not found. Use /start.")
        return

    balance = user.get("balance", 0)
    await message.reply_text(f"Your current balance is {balance} kyat.\nသင့်လက်ကျန်ငွေ: {balance} ကျပ်")
    logger.info(f"Balance for {user_id}: {balance}")

def register_handlers(application: Application):
    application.add_handler(CallbackQueryHandler(check_balance, pattern="^balance$"))
    application.add_handler(CommandHandler("balance", check_balance))