from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
from config import ADMIN_IDS
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.warning(f"Unauthorized /check attempt by user {user_id}")
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("Usage: /check <user_id>")
            logger.info(f"Invalid /check syntax by user {user_id}: {args}")
            return

        target_user_id = args[0]
        user = await db.get_user(target_user_id)
        if not user:
            await update.message.reply_text(f"User {target_user_id} not found.")
            logger.info(f"User {target_user_id} not found for /check by user {user_id}")
            return

        balance = user.get("balance", 0)
        messages = user.get("messages", 0)
        group_messages = user.get("group_messages", {}).get("-1002061898677", 0)
        name = user.get("name", "Unknown")

        message = (
            f"User {target_user_id} ({name}):\n"
            f"Balance: {balance:.2f} kyat\n"
            f"Total Messages: {messages}\n"
            f"Messages in -1002061898677: {group_messages}"
        )
        await update.message.reply_text(message)
        logger.info(f"User {user_id} checked stats for user {target_user_id}")

    except Exception as e:
        await update.message.reply_text("Error processing /check. Try again later.")
        logger.error(f"Error in /check for user {user_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("check", check))