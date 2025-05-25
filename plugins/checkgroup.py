from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import GROUP_CHAT_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def checkgroup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Checkgroup command by user {user_id} in chat {chat_id}")

    if await db.check_rate_limit(user_id):
        logger.warning(f"Rate limit exceeded for user {user_id}")
        await update.message.reply_text("You're sending commands too quickly. Please wait a moment.")
        return

    approved_groups = await db.get_approved_groups()
    if not approved_groups:
        logger.info("No approved groups found")
        await update.message.reply_text("No approved groups found.")
        return

    response = "Group Message Counts:\n"
    for group_id in approved_groups:
        if group_id not in GROUP_CHAT_IDS:
            continue
        message_count = await db.get_group_message_count(group_id)
        response += f"Group {group_id}: {message_count} messages\n"
        logger.info(f"Group {group_id} has {message_count} messages")

    await update.message.reply_text(response)
    logger.info(f"Sent group message counts to user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering checkgroup handler")
    application.add_handler(CommandHandler("checkgroup", checkgroup))