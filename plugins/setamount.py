from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import ADMIN_IDS, LOG_CHANNEL_ID

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def setamount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Setamount command initiated by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized setamount attempt by user {user_id}")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /setamount <number>")
        logger.info(f"Invalid arguments provided by user {user_id}: {context.args}")
        return

    amount = int(context.args[0])
    if amount <= 0:
        await update.message.reply_text("Amount must be a positive number.")
        logger.info(f"Invalid amount {amount} provided by user {user_id}")
        return

    success = await db.set_referral_reward(amount)
    if success:
        await update.message.reply_text(f"Referral reward set to {amount} kyat.")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin {user_id} set referral reward to {amount} kyat."
        )
        logger.info(f"Referral reward set to {amount} kyat by admin {user_id}")
    else:
        await update.message.reply_text("Failed to set referral reward. Please try again.")
        logger.error(f"Failed to set referral reward to {amount} by user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering setamount handlers")
    application.add_handler(CommandHandler("setamount", setamount))