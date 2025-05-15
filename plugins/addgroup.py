from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def addgroup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Addgroup command initiated by user {user_id} in chat {chat_id}")

    # Restrict to admin (user ID 5062124930)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized addgroup attempt by user {user_id}")
        return

    # Check if a group ID is provided
    if not context.args:
        await update.message.reply_text("Please provide a group ID. Usage: /addgroup <group_id>")
        logger.info(f"No group ID provided by user {user_id}")
        return

    group_id = context.args[0]
    # Validate group ID format (should start with -100)
    if not group_id.startswith("-100"):
        await update.message.reply_text("Invalid group ID. It should start with -100 (e.g., -1002061898677).")
        logger.info(f"Invalid group ID {group_id} provided by user {user_id}")
        return

    # Add the group to the database
    success = await db.add_group(group_id)
    if success:
        await update.message.reply_text(f"Group {group_id} has been added for message counting.")
        logger.info(f"Group {group_id} added by admin {user_id}")

        # Log to admin channel
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin added group {group_id} for message counting."
        )
    else:
        await update.message.reply_text("Failed to add the group. Please try again.")
        logger.error(f"Failed to add group {group_id} by user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering addgroup handlers")
    application.add_handler(CommandHandler("addgroup", addgroup))