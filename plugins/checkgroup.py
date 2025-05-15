from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def checkgroup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Checkgroup command initiated by user {user_id} in chat {chat_id}")

    # Restrict to admin (user ID 5062124930)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized checkgroup attempt by user {user_id}")
        return

    # Check if a group ID is provided
    if not context.args:
        await update.message.reply_text("Please provide a group ID. Usage: /checkgroup <group_id>")
        logger.info(f"No group ID provided by user {user_id}")
        return

    group_id = context.args[0]
    # Validate group ID format
    if not group_id.startswith("-100"):
        await update.message.reply_text("Invalid group ID. It should start with -100 (e.g., -1002061898677).")
        logger.info(f"Invalid group ID {group_id} provided by user {user_id}")
        return

    # Check if the group is approved (only -1002061898677 is counted now)
    if group_id != "-1002061898677":
        await update.message.reply_text(f"Only group -1002061898677 is approved for message counting.")
        logger.info(f"Group {group_id} not approved, checked by user {user_id}")
        return

    # Get total messages in the group
    total_messages = await db.get_group_message_count(group_id)
    await update.message.reply_text(
        f"Group {group_id} is approved for message counting.\n"
        f"Total messages counted: {total_messages}\n"
        f"Earning rate: 1 message = 1 kyat"
    )
    logger.info(f"Checked group {group_id} for user {user_id}: {total_messages} messages")

    # Log to admin channel
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"Admin checked group {group_id}: {total_messages} messages counted. Earning rate: 1 message = 1 kyat."
    )

def register_handlers(application: Application):
    logger.info("Registering checkgroup handlers")
    application.add_handler(CommandHandler("checkgroup", checkgroup))