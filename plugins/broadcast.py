from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Broadcast command initiated by user {user_id} in chat {chat_id}")

    # Restrict to admin (user ID 5062124930)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized broadcast attempt by user {user_id}")
        return

    # Check if a message is provided
    if not context.args:
        await update.message.reply_text("Please provide a message to broadcast. Usage: /broadcast <message>")
        logger.info(f"No message provided by user {user_id}")
        return

    message = " ".join(context.args)
    # Simulate broadcasting (replace with actual logic to send to all users)
    await update.message.reply_text(f"Broadcasting: {message}")
    logger.info(f"Broadcast initiated by user {user_id} with message: {message}")

    # Log to admin channel
    await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"Broadcast by {update.effective_user.full_name}: {message}")

def register_handlers(application: Application):
    logger.info("Registering broadcast handlers")
    application.add_handler(CommandHandler("broadcast", broadcast))