from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import ADMIN_IDS, LOG_CHANNEL_ID
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def set_invite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"/setinvite command initiated by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Only admins can set invite requirements.")
        logger.info(f"User {user_id} attempted /setinvite but is not an admin")
        return

    if not context.args:
        await update.message.reply_text("Please provide the number of required invites (e.g., /setinvite 20).")
        logger.info(f"User {user_id} provided no arguments for /setinvite")
        return

    try:
        required_invites = int(context.args[0])
        if required_invites < 0:
            raise ValueError("Number must be non-negative")
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")
        logger.info(f"User {user_id} provided invalid number for /setinvite")
        return

    db.settings_collection.update_one(
        {"_id": "invite_settings"},
        {"$set": {"required_invites": required_invites}},
        upsert=True
    )
    message = f"Required invites set to: {required_invites}"

    try:
        await update.message.reply_text(message)
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin {user_id} set required invites to: {required_invites}"
        )
        logger.info(f"Set required invites to {required_invites} by user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send /setinvite response to user {user_id}: {e}")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Failed to send /setinvite response to {user_id}: {e}"
        )

def register_handlers(application: Application):
    logger.info("Registering setinvite handlers")
    application.add_handler(CommandHandler("setinvite", set_invite))