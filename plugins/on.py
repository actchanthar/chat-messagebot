from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from config import COUNT_MESSAGES

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    global COUNT_MESSAGES
    COUNT_MESSAGES = True
    await update.message.reply_text("Message counting enabled.")
    logger.info("Message counting enabled by admin")

def register_handlers(application: Application):
    logger.info("Registering on handler")
    application.add_handler(CommandHandler("on", on))