from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def referral_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found. Start with /start.")
        return

    invite_count = user.get("invite_count", 0)
    reward = invite_count * 25
    message = (
        f"Your Referral Stats:\n"
        f"Invites: {invite_count}\n"
        f"Reward Earned: {reward} kyats\n"
        f"Use /start to get your referral link!"
    )
    await update.message.reply_text(message)

def register_handlers(application):
    application.add_handler(CommandHandler("referral_users", referral_users))