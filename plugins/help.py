from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from config import BOT_USERNAME

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Help command by user {user_id} in chat {chat_id}")

    help_text = (
        f"Welcome to {BOT_USERNAME}!\n"
        "Here are the available commands:\n\n"
        "/start - Start