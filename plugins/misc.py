from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Admin user ID (replace with your admin's Telegram user ID)
ADMIN_USER_ID = "5062124930"

async def set_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"SetMessage command initiated by user {user_id}")

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("This command is admin-only.")
        logger.warning(f"Non-admin user {user_id} attempted /setmessage")
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /setmessage <number>")
        logger.info(f"Invalid arguments for /setmessage by user {user_id}")
        return

    try:
        messages_per_kyat = int(context.args[0])
        if messages_per_kyat <= 0:
            raise ValueError("Number must be positive")
        # Store the messages per kyat (assuming it's stored in a config or database)
        await db.update_user("global_config", {"$set": {"messages_per_kyat": messages_per_kyat}}, upsert=True)
        logger.info(f"Set messages per kyat to {messages_per_kyat} by user {user_id}")
        await update.message.reply_text(f"Messages per kyat set to {messages_per_kyat}.")
    except ValueError as e:
        logger.error(f"Invalid number for /setmessage by user {user_id}: {e}")
        await update.message.reply_text("Please provide a valid positive number.")
    except Exception as e:
        logger.error(f"Error setting messages per kyat for user {user_id}: {e}")
        await update.message.reply_text("Error setting messages per kyat. Please try again later.")

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
    application.add_handler(CommandHandler("setmessage", set_message))