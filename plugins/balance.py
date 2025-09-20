from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from database.database import db
import logging
from config import CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(update.effective_user.id if not query else query.from_user.id)
    
    user = await db.get_user(user_id)
    if not user:
        await (query.message if query else update.message).reply_text("User not found. Please start with /start.")
        return

    balance = user.get("balance", 0)
    displayed_balance = max(0, balance)
    balance_rounded = int(displayed_balance)
    
    reply_text = (
        f"💰 Your current balance is {balance_rounded} {CURRENCY}.\n"
        f"သင့်လက်ကျန်ငွေသည် {balance_rounded} ကျပ်ဖြစ်ပါသည်။"
    )
    
    await (query.message if query else update.message).reply_text(
        reply_text, 
        reply_markup=query.message.reply_markup if query else None
    )

def register_handlers(application: Application):
    application.add_handler(CallbackQueryHandler(check_balance, pattern="^balance$"))
    application.add_handler(CommandHandler("balance", check_balance))
    