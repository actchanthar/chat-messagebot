from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Balance check by user {user_id}")

    user = await db.get_user(user_id)
    if not user:
        logger.info(f"User {user_id} not found")
        await update.message.reply_text("User not found. Please start the bot with /start.")
        return

    balance = user.get("balance", 0)
    messages = user.get("messages", 0)
    invites = len(user.get("invited_users", [])) if "invited_users" in user else user.get("invites", 0)

    message = (
        f"Your Balance: {balance} kyat\n"
        f"Total Messages: {messages}\n"
        f"Total Invites: {invites}"
    )
    await update.message.reply_text(message)
    logger.info(f"Sent balance info to user {user_id}: balance={balance}, messages={messages}, invites={invites}")

async def balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    logger.info(f"Balance callback by user {user_id}")

    user = await db.get_user(user_id)
    if not user:
        logger.info(f"User {user_id} not found")
        await query.message.reply_text("User not found.")
        return

    balance = user.get("balance", 0)
    messages = user.get("messages", 0)
    invites = len(user.get("invited_users", [])) if "invited_users" in user else user.get("invites", 0)

    message = (
        f"Your Balance: {balance} kyat\n"
        f"Total Messages: {messages}\n"
        f"Total Invites: {invites}"
    )
    await query.message.reply_text(message)
    logger.info(f"Sent balance info to user {user_id}: balance={balance}, messages={messages}, invites={invites}")

def register_handlers(application: Application):
    logger.info("Registering balance handlers")
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CallbackQueryHandler(balance_callback, pattern="^balance$"))