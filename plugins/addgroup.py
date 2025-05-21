from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import ADMIN_IDS, LOG_CHANNEL_ID
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def addgroup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"/addgroup command initiated by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Only admins can add groups.")
        logger.info(f"User {user_id} attempted /addgroup but is not an admin")
        return

    if not context.args:
        await update.message.reply_text("Please provide a group chat ID (e.g., /addgroup -1001234567890).")
        logger.info(f"User {user_id} provided no arguments for /addgroup")
        return

    group_id = context.args[0]
    if not group_id.startswith("-100") or not group_id[1:].isdigit():
        await update.message.reply_text("Invalid group chat ID. It should start with -100 followed by numbers.")
        logger.info(f"User {user_id} provided invalid group ID {group_id} for /addgroup")
        return

    channels = db.get_required_channels()
    if group_id not in channels:
        channels.append(group_id)
        db.set_required_channels(channels)
        message = f"Group {group_id} added to required channels."
    else:
        message = f"Group {group_id} is already in required channels."

    try:
        await update.message.reply_text(message)
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin {user_id} added group {group_id} to required channels."
        )
        logger.info(f"Added group {group_id} by user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send /addgroup response to user {user_id}: {e}")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Failed to send /addgroup response to {user_id}: {e}"
        )

def register_handlers(application: Application):
    logger.info("Registering addgroup handlers")
    application.add_handler(CommandHandler("addgroup", addgroup))