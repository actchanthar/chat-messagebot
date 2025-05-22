from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.warning(f"Unauthorized /on attempt by user {user_id}")
        return

    try:
        if await db.set_count_messages(True):
            await update.message.reply_text("Message counting enabled.")
            logger.info(f"User {user_id} enabled message counting")
        else:
            await update.message.reply_text("Failed to enable message counting.")
            logger.error(f"Failed to enable message counting by user {user_id}")
    except Exception as e:
        await update.message.reply_text("Failed to enable message counting.")
        logger.error(f"Error in /on for user {user_id}: {e}")

async def off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.warning(f"Unauthorized /off attempt by user {user_id}")
        return

    try:
        if await db.set_count_messages(False):
            await update.message.reply_text("Message counting disabled.")
            logger.info(f"User {user_id} disabled message counting")
        else:
            await update.message.reply_text("Failed to disable message counting.")
            logger.error(f"Failed to disable message counting by user {user_id}")
    except Exception as e:
        await update.message.reply_text("Failed to disable message counting.")
        logger.error(f"Error in /off for user {user_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("on", on))
    application.add_handler(CommandHandler("off", off))