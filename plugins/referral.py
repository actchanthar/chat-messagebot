from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def referral_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Referral_users command by user {user_id}")

    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("Please start with /start first.")
        return

    referrals = await db.get_referrals(user_id)
    channels = await db.get_force_sub_channels()
    valid_referrals = sum(1 for ref in referrals if all(await db.check_user_subscription(ref, ch) for ch in channels))
    await update.message.reply_text(f"You have {valid_referrals} valid referrals.")

def register_handlers(application: Application):
    logger.info("Registering referral handlers")
    application.add_handler(CommandHandler("referral_users", referral_users))