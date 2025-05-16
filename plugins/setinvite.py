from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def setinvite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"SetInvite command initiated by user {user_id} in chat {chat_id}")

    # Restrict to admin (user ID 5062124930)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized SetInvite attempt by user {user_id}")
        return

    # Check if a number is provided
    if not context.args:
        await update.message.reply_text("Please provide the number of required invites. Usage: /setinvite <number>")
        logger.info(f"No number provided by user {user_id}")
        return

    try:
        required_invites = int(context.args[0])
        if required_invites < 0:
            await update.message.reply_text("Please provide a non-negative number.")
            return
    except ValueError:
        await update.message.reply_text("Please provide a valid number. Usage: /setinvite <number>")
        return

    success = await db.set_required_invites(required_invites)
    if success:
        await update.message.reply_text(f"Required invites set to: {required_invites}")
        logger.info(f"Required invites set to {required_invites} by admin {user_id}")

        # Log to admin channel
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin set required invites to: {required_invites}"
        )
    else:
        await update.message.reply_text("Failed to set required invites. Please try again.")
        logger.error(f"Failed to set required invites by user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering setinvite handlers")
    application.add_handler(CommandHandler("setinvite", setinvite))