from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import LOG_CHANNEL_ID
from database.database import db
import datetime
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"/help command initiated by user {user_id} in chat {chat_id}")

    message = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/top - View top users by invites\n"
        "/withdraw - Withdraw funds\n"
        "/users or /dfusers - Delete failed broadcast users (admin)\n"
        "/broadcast <message> - Broadcast a message (admin)\n"
        "/SetPhoneBill <text> - Set phone bill reward (admin)\n"
        "/addbonus <user_id> <amount> - Add bonus (admin)\n"
        "/setinvite <number> - Set required invites (admin)"
    )

    # Track help command usage
    db.update_user(user_id, {"last_help": datetime.datetime.now()})

    try:
        await update.message.reply_text(message)
        logger.info(f"Sent help message to user {user_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send /help response to user {user_id}: {e}")
        try:
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Failed to send /help response to {user_id}: {e}"
            )
        except Exception as log_error:
            logger.error(f"Failed to log /help error to {LOG_CHANNEL_ID}: {log_error}")

def register_handlers(application: Application):
    logger.info("Registering help handlers")
    application.add_handler(CommandHandler("help", help))