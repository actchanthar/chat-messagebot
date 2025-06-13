from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID, ADMIN_IDS

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def checkgroup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Checkgroup command initiated by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized checkgroup attempt by user {user_id}")
        return

    if not context.args:
        await update.message.reply_text("Please provide a group ID. Usage: /checkgroup <group_id>")
        logger.info(f"No group ID provided by user {user_id}")
        return

    group_id = context.args[0]
    if group_id != "-1002061898677":
        await update.message.reply_text("Only group -1002061898677 is approved for message counting.")
        logger.info(f"Group {group_id} not approved, checked by user {user_id}")
        return

    try:
        total_messages = await db.get_group_message_count(group_id)
        message_rate = await db.get_message_rate()
        await update.message.reply_text(
            f"Group {group_id} is approved for message counting.\n"
            f"Total messages counted: {total_messages}\n"
            f"Earning rate: {message_rate} messages = 1 kyat"
        )
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin checked group {group_id}: {total_messages} messages counted. Earning rate: {message_rate} messages = 1 kyat."
        )
        logger.info(f"Checked group {group_id} for user {user_id}: {total_messages} messages")
    except Exception as e:
        logger.error(f"Error checking group {group_id} for user {user_id}: {e}")
        await update.message.reply_text("An error occurred while checking the group. Please try again.")

def register_handlers(application: Application):
    logger.info("Registering checkgroup handlers")
    application.add_handler(CommandHandler("checkgroup", checkgroup))