from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Admin user ID (replace with your admin's Telegram user ID)
ADMIN_USER_ID = "5062124930"

async def rest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Rest command initiated by user {user_id}")

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("This command is admin-only.")
        logger.warning(f"Non-admin user {user_id} attempted /rest")
        return

    try:
        # Reset message counts for all users
        await db.users.update_many(
            {},
            {"$set": {"group_messages": {}}}
        )
        logger.info("Reset message counts for all users")
        await update.message.reply_text("Message counts reset successfully.")
    except Exception as e:
        logger.error(f"Error resetting message counts: {e}")
        await update.message.reply_text("Error resetting message counts. Please try again later.")

def register_handlers(application: Application):
    logger.info("Registering misc handlers")
    application.add_handler(CommandHandler("rest", rest))