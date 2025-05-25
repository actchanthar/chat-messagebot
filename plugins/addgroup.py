from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import ADMIN_IDS, LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def addgroup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Addgroup command by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized addgroup attempt by user {user_id}")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        logger.info(f"No group ID provided by user {user_id}")
        await update.message.reply_text("Please provide a group ID. Usage: /addgroup <group_id>")
        return

    group_id = context.args[0]
    result = await db.add_group(group_id)
    if result == "exists":
        logger.info(f"Group {group_id} already approved")
        await update.message.reply_text(f"Group {group_id} is already approved.")
    elif result:
        logger.info(f"Group {group_id} added by user {user_id}")
        await update.message.reply_text(f"Group {group_id} has been added.")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Group {group_id} added by admin {user_id}."
        )
    else:
        logger.error(f"Failed to add group {group_id}")
        await update.message.reply_text("Failed to add group. Please try again.")

def register_handlers(application: Application):
    logger.info("Registering addgroup handler")
    application.add_handler(CommandHandler("addgroup", addgroup))