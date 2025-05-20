from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def setmessage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setmessage <number>")
        return

    try:
        number = int(context.args[0])
        if number <= 0:
            raise ValueError
        await db.set_setting("messages_per_kyat", number)
        await update.message.reply_text(f"Set {number} messages per kyat.")
    except ValueError:
        await update.message.reply_text("Please provide a valid positive number.")

def register_handlers(application: Application):
    logger.info("Registering setmessage handlers")
    application.add_handler(CommandHandler("setmessage", setmessage))