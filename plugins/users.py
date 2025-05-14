# plugins/users.py
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define admin user IDs (consistent with broadcast.py)
ADMIN_IDS = ["5062124930"]

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Users command initiated by user {user_id}")

    # Check if the user is an admin
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"User {user_id} attempted to use /users but is not an admin")
        return

    try:
        # Test database connectivity
        logger.info("Attempting to fetch all users from the database")
        all_users = await db.get_all_users()
        if all_users is None:
            logger.error("db.get_all_users() returned None, possible database issue")
            await update.message.reply_text("Error: Database returned no data. Please contact support.")
            return

        user_count = len(all_users)
        logger.info(f"Retrieved {user_count} users from the database: {all_users}")
        await update.message.reply_text(f"There are currently {user_count} users in the bot's database.")
    except Exception as e:
        logger.error(f"Failed to retrieve user count: {str(e)}", exc_info=True)
        await update.message.reply_text(f"Error retrieving user count: {str(e)}. Please try again later.")

def register_handlers(application: Application):
    logger.info("Registering users handlers")
    application.add_handler(CommandHandler("users", users))