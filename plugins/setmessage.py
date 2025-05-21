from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def setmessage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setmessage <messages_per_kyat>")
        return

    try:
        messages_per_kyat = int(context.args[0])
        if messages_per_kyat <= 0:
            await update.message.reply_text("Messages per kyat must be positive.")
            return
        if await db.set_message_rate(messages_per_kyat):
            await update.message.reply_text(f"Set message rate to {messages_per_kyat} messages per kyat.")
            await context.bot.send_message(
                LOG_CHANNEL_ID,
                f"Admin set message rate to {messages_per_kyat} messages per kyat."
            )
        else:
            await update.message.reply_text("Failed to set message rate.")
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")

def register_handlers(application):
    logger.info("Registering setmessage handlers")
    application.add_handler(CommandHandler("setmessage", setmessage))