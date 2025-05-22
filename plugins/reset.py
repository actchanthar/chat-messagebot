from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    admin_ids = ["5062124930"]  # Replace with your admin user IDs

    if user_id not in admin_ids:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.warning(f"Unauthorized reset attempt by user {user_id}")
        return

    try:
        result = await db.users.update_many(
            {},
            {
                "$set": {
                    "messages": 0,
                    "group_messages": {"-1002061898677": 0},
                    "invite_count": 0,
                    "invites": []
                }
            }
        )
        await update.message.reply_text(f"Reset complete. Modified {result.modified_count} users.")
        logger.info(f"User {user_id} reset messages and invites for {result.modified_count} users")
    except Exception as e:
        await update.message.reply_text("Failed to reset data.")
        logger.error(f"Error in reset for user {user_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("reset", reset))