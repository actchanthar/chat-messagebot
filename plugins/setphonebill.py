from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import ADMIN_IDS, LOG_CHANNEL_ID
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def set_phone_bill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"SetPhoneBill command initiated by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Only admins can set the phone bill reward.")
        logger.info(f"User {user_id} attempted /SetPhoneBill but is not an admin")
        return

    if not context.args:
        await update.message.reply_text("Please provide the phone bill reward text (e.g., /SetPhoneBill 1000 Kyat).")
        logger.info(f"User {user_id} provided no arguments for /SetPhoneBill")
        return

    reward_text = " ".join(context.args)
    db.set_phone_bill_reward_text(reward_text)
    message = f"Phone bill reward set to: {reward_text}"

    try:
        await update.message.reply_text(message)
        logger.info(f"Set phone bill reward text to '{reward_text}' by user {user_id}")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin {user_id} set phone bill reward to: {reward_text}"
        )
    except Exception as e:
        logger.error(f"Failed to send /SetPhoneBill response to user {user_id}: {e}")
        try:
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Failed to send /SetPhoneBill response to {user_id}: {e}"
            )
        except Exception as log_error:
            logger.error(f"Failed to log /SetPhoneBill error to {LOG_CHANNEL_ID}: {log_error}")

def register_handlers(application: Application):
    logger.info("Registering setphonebill handlers")
    application.add_handler(CommandHandler("SetPhoneBill", set_phone_bill))