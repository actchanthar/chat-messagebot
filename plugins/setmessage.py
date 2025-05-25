from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def set_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Setmessage command by user {user_id}")

    if user_id not in ADMIN_IDS:
        logger.info(f"User {user_id} not admin")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args or not context.args[0].isdigit():
        logger.info(f"Invalid arguments for /setmessage: {context.args}")
        await update.message.reply_text("Usage: /setmessage <number>")
        return

    messages_per_kyat = int(context.args[0])
    try:
        await db.set_messages_per_kyat(messages_per_kyat)
        logger.info(f"Set messages_per_kyat to {messages_per_kyat}")
        await update.message.reply_text(f"Messages per kyat set to {messages_per_kyat}.")
    except Exception as e:
        logger.error(f"Error setting messages_per_kyat: {str(e)}")
        await update.message.reply_text("Error setting messages per kyat. Please try again.")

def register_handlers(application: Application):
    logger.info("Registering setmessage handler")
    application.add_handler(CommandHandler("setmessage", set_message))