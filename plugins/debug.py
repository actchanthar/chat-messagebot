# plugins/debug.py
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import logging

logger = logging.getLogger(__name__)

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    logger.info(f"Debug command called by user {user_id} in chat {chat_id}")
    await update.message.reply_text(
        f"Debug Info:\n"
        f"User ID: {user_id}\n"
        f"Chat ID: {chat_id}\n"
        f"Chat Type: {update.effective_chat.type}\n"
        f"Context Data: {context.user_data}"
    )

def register_handlers(application):
    logger.info("Registering debug handlers")
    application.add_handler(CommandHandler("debug", debug))