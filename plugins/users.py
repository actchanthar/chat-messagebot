from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
from config import ADMIN_IDS
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.warning(f"Unauthorized /users attempt by user {user_id}")
        return

    try:
        total_users = await db.get_total_users()
        active_users = await db.users.count_documents({"messages": {"$gt": 0}})
        message = (
            f"User Statistics:\n"
            f"Total Users: {total_users}\n"
            f"Active Users (with messages): {active_users}"
        )
        await update.message.reply_text(message)
        logger.info(f"User {user_id} ran /users")
    except Exception as e:
        await update.message.reply_text("Failed to retrieve user stats.")
        logger.error(f"Error in /users for user {user_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("users", users))