from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def grok(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Grok command initiated by user {user_id}")
    await update.message.reply_text(
        "Hello! I'm ACTAI, developed by A Sama, here to assist you. 😄 Ask me anything or let me help with your bot!"
    )
    logger.info(f"Responded to /grok by user {user_id}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("grok", grok))
    logger.info("Grok command handler registered successfully")