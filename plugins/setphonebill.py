from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import ADMIN_IDS, LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def setphonebill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Setphonebill command by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized setphonebill attempt by user {user_id}")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        logger.info(f"No reward text provided by user {user_id}")
        await update.message.reply_text("Please provide the reward text. Usage: /setphonebill <reward_text>")
        return

    reward_text = " ".join(context.args)
    if await db.set_phone_bill_reward(reward_text):
        logger.info(f"Phone bill reward set to '{reward_text}' by user {user_id}")
        await update.message.reply_text(f"Phone bill reward set to: {reward_text}")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Phone bill reward set to '{reward_text}' by admin {user_id}."
        )
    else:
        logger.error(f"Failed to set phone bill reward to '{reward_text}'")
        await update.message.reply_text("Failed to set phone bill reward. Please try again.")

def register_handlers(application: Application):
    logger.info("Registering setphonebill handler")
    application.add_handler(CommandHandler("setphonebill", setphonebill))