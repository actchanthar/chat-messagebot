from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Balance check initiated by user {user_id} via /balance command")

    if db is None:
        logger.error("Database not initialized, cannot process /balance")
        await update.message.reply_text("Bot is experiencing issues. Please try again later.")
        return

    user = await db.get_user(user_id)
    if not user:
        logger.info(f"User {user_id} not found, prompting to start")
        await update.message.reply_text("You haven't started yet! Use /start to begin.")
        return

    balance = user.get("balance", 0)
    messages = user.get("messages", 0)
    group_messages = sum(user.get("group_messages", {}).values())
    referrals = len(user.get("referrals", []))

    message = (
        f"💰 Your Balance: {balance:.2f} {CURRENCY}\n"
        f"📩 Total Messages: {messages}\n"
        f"👥 Group Messages: {group_messages}\n"
        f"🤝 Referrals: {referrals}"
    )
    await update.message.reply_text(message)
    logger.info(f"Sent balance info to user {user_id}: {balance:.2f} {CURRENCY}")

def register_handlers(application: Application):
    logger.info("Registering balance handlers")
    application.add_handler(CommandHandler("balance", check_balance))