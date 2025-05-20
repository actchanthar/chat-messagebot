from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def checkgroup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized.")
        return

    try:
        groups = await db.get_approved_groups()
        if not groups:
            await update.message.reply_text("No approved groups found.")
            return

        message = "Group Message Counts:\n\n"
        for group_id in groups:
            count = await db.get_group_message_count(group_id)
            message += f"Group {group_id}: {count} messages\n"

        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in checkgroup for user {user_id}: {e}")
        await update.message.reply_text("An error occurred while checking groups.")

def register_handlers(application: Application):
    logger.info("Registering checkgroup handlers")
    application.add_handler(CommandHandler("checkgroup", checkgroup, block=False))