from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Users command initiated by user {user_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"User {user_id} attempted to use /users but is not an admin")
        return

    try:
        all_users = await db.get_all_users()
        if all_users is None:
            logger.error("db.get_all_users() returned None")
            await update.message.reply_text("Error: Database returned no data.")
            return

        user_count = len(all_users)
        logger.info(f"Retrieved {user_count} users from the database")
        await update.message.reply_text(f"There are currently {user_count} users in the bot's database.")
    except Exception as e:
        logger.error(f"Failed to retrieve user count: {str(e)}")
        await update.message.reply_text(f"Error retrieving user count: {str(e)}.")

def register_handlers(application: Application):
    logger.info("Registering users handlers")
    application.add_handler(CommandHandler("users", users))