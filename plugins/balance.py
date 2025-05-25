from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database.database import db
import logging
from config import CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    source = "command" if update.message else "button"
    logger.info(f"Balance command by user {user_id} in chat {chat_id} via {source}")

    if update.callback_query:
        await update.callback_query.answer()

    user = await db.get_user(user_id)
    if not user:
        reply_text = "User not found. Please start with /start."
        if update.message:
            await update.message.reply_text(reply_text)
        else:
            await update.callback_query.message.reply_text(reply_text)
        return

    balance = user.get("balance", 0)
    messages = user.get("messages", 0)
    invites = await db.get_invites(user_id)
    reply_text = (
        f"Your Balance: {balance} {CURRENCY}\n"
        f"Total Messages: {messages}\n"
        f"Total Invites: {invites}"
    )

    if update.message:
        await update.message.reply_text(reply_text)
    else:
        await update.callback_query.message.reply_text(reply_text)
    logger.info(f"Sent balance info to user {user_id}: {balance} {CURRENCY}")

def register_handlers(application: Application):
    logger.info("Registering balance handlers")
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CallbackQueryHandler(balance, pattern="^balance$"))