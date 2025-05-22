from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import ADMIN_IDS
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.warning(f"Unauthorized /admin attempt by user {user_id}")
        return

    try:
        message = (
            "Admin Commands:\n"
            "/ban <user_id> - Ban a user\n"
            "/unban <user_id> - Unban a user\n"
            "/setrate <value> - Set message rate (msg/kyat)"
        )
        await update.message.reply_text(message)
        logger.info(f"User {user_id} ran /admin")
    except Exception as e:
        await update.message.reply_text("Failed to process /admin.")
        logger.error(f"Error in /admin for user {user_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("admin", admin))