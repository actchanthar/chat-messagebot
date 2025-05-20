from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Admin user ID (replace with your admin's Telegram user ID)
ADMIN_USER_ID = "5062124930"

async def set_phone_bill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"SetPhoneBill command initiated by user {user_id}")

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("This command is admin-only.")
        logger.warning(f"Non-admin user {user_id} attempted /SetPhoneBill")
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /SetPhoneBill <reward_text>")
        logger.info(f"Invalid arguments for /SetPhoneBill by user {user_id}")
        return

    reward_text = context.args[0]
    try:
        # Store the reward text (assuming it's stored in a config or database)
        await db.update_user("global_config", {"$set": {"phone_bill_reward": reward_text}}, upsert=True)
        logger.info(f"Set phone bill reward to '{reward_text}' by user {user_id}")
        await update.message.reply_text(f"Phone bill reward set to '{reward_text}'.")
    except Exception as e:
        logger.error(f"Error setting phone bill reward for user {user_id}: {e}")
        await update.message.reply_text("Error setting phone bill reward. Please try again later.")

def register_handlers(application: Application):
    logger.info("Registering setphonebill handlers")
    application.add_handler(CommandHandler("SetPhoneBill", set_phone_bill))