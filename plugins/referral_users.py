from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def referral_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Referral_users command by user {user_id}")

    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found. Please start with /start.")
        return

    invite_requirement = await db.get_invite_requirement()
    invites = user.get("invites", 0)
    referral_link = f"t.me/{context.bot.username}?start={user_id}"
    message = (
        f"Your referral link: {referral_link}\n"
        f"Invites: {invites}/{invite_requirement}\n"
        f"Invite {invite_requirement} users who join the required channels to withdraw. "
        f"You earn 25 kyat per valid invite, and they earn 50 kyat!"
    )
    await update.message.reply_text(message)
    logger.info(f"Sent referral info to user {user_id}")

def register_handlers(application):
    logger.info("Registering referral_users handlers")
    application.add_handler(CommandHandler("referral_users", referral_users))