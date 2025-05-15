from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def setphonebill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"SetPhoneBill command initiated by user {user_id} in chat {chat_id}")

    # Check rate limit silently
    if await db.check_rate_limit(user_id):
        logger.warning(f"Rate limit enforced for user {user_id} in chat {chat_id}")
        return  # Do not reply, just skip processing

    # Restrict to admin (user ID 5062124930)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized SetPhoneBill attempt by user {user_id}")
        return

    # Check if a reward text is provided
    if not context.args:
        await update.message.reply_text("Please provide the reward text. Usage: /SetPhoneBill <reward_text>")
        logger.info(f"No reward text provided by user {user_id}")
        return

    reward_text = " ".join(context.args)
    success = await db.set_phone_bill_reward(reward_text)
    if success:
        await update.message.reply_text(f"Phone Bill reward set to: {reward_text}")
        logger.info(f"Phone Bill reward set to '{reward_text}' by admin {user_id}")

        # Log to admin channel
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin set Phone Bill reward to: {reward_text}"
        )
    else:
        await update.message.reply_text("Failed to set Phone Bill reward. Please try again.")
        logger.error(f"Failed to set Phone Bill reward by user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering setphonebill handlers")
    application.add_handler(CommandHandler("SetPhoneBill", setphonebill))