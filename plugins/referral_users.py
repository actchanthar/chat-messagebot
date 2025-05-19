# plugins/referral_users.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def referral_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Referral_users command initiated by user {user_id}")

    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found. Please start with /start.")
        return

    settings = await db.get_settings()
    required_invites = settings.get("required_invites", 15)
    channels = settings.get("force_sub_channels", [])
    invites = user.get("invites", 0)
    referral_link = user.get("referral_link", f"https://t.me/{context.bot.username}?start={user_id}")

    if not channels:
        await update.message.reply_text("No force-sub channels configured. Contact the admin.")
        return

    keyboard = [[InlineKeyboardButton(f"Join {c['name']}", url=f"https://t.me/{c['id'].replace('-100', '')}")] for c in channels]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Your referral link: {referral_link}\n"
        f"Current invites: {invites}/{required_invites}\n"
        f"Invite {required_invites} users who join our channel(s) to withdraw.\n"
        f"Earn 25 kyat per successful invite. New users get 50 kyat for joining.\n"
        f"Please join the following channel(s) to make your invites count:",
        reply_markup=reply_markup
    )
    logger.info(f"Sent referral info to user {user_id}")

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: str, channel_id: str) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=int(user_id))
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id} in channel {channel_id}: {e}")
        return False

def register_handlers(application: Application):
    logger.info("Registering referral_users handlers")
    application.add_handler(CommandHandler("referral_users", referral_users))