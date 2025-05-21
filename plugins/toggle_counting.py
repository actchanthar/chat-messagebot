from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def enable_counting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if await db.toggle_message_counting(True):
        await update.message.reply_text("Message counting enabled.")
        await context.bot.send_message(LOG_CHANNEL_ID, "Admin enabled message counting.")
    else:
        await update.message.reply_text("Failed to enable message counting.")

async def disable_counting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if await db.toggle_message_counting(False):
        await update.message.reply_text("Message counting disabled.")
        await context.bot.send_message(LOG_CHANNEL_ID, "Admin disabled message counting.")
    else:
        await update.message.reply_text("Failed to disable message counting.")

def register_handlers(application):
    logger.info("Registering toggle counting handlers")
    application.add_handler(CommandHandler("on", enable_counting))
    application.add_handler(CommandHandler("off", disable_counting))