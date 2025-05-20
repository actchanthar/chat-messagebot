import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Received /start from user {user_id}")

    if db is None:
        logger.error("Database not initialized")
        await update.message.reply_text("Bot is experiencing issues. Please try again later.")
        return

    user = await db.get_user(user_id)
    if not user:
        name = update.effective_user.full_name
        user = await db.create_user(user_id, name)
        if not user:
            logger.error(f"Failed to create user {user_id}")
            await update.message.reply_text("Error creating user. Try again later.")
            return

    await update.message.reply_text(f"Welcome, {user['name']}! You can earn by sending messages.")
    logger.debug(f"Sent welcome to user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering start handler")
    application.add_handler(CommandHandler("start", start))