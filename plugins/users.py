from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import CURRENCY, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Users command by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized users command attempt by user {user_id}")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    all_users = await db.get_all_users()
    total_users = len(all_users)
    total_messages = sum(user.get("messages", 0) for user in all_users)
    total_balance = sum(user.get("balance", 0) for user in all_users)
    total_withdrawn = sum(user.get("withdrawn_today", 0) for user in all_users)

    response = (
        f"Total Users: {total_users}\n"
        f"Total Messages: {total_messages}\n"
        f"Total Balance: {total_balance} {CURRENCY}\n"
        f"Total Withdrawn Today: {total_withdrawn} {CURRENCY}"
    )
    await update.message.reply_text(response)
    logger.info(f"Sent user stats to admin {user_id}")

async def referral_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Referral_users command by user {user_id} in chat {chat_id}")

    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found. Please start with /start.")
        return

    invite_count = await db.get_invites(user_id)
    referral_link = user.get("referral_link", f"https://t.me/ACTMoneyBot?start={user_id}")
    await update.message.reply_text(
        f"Your Referral Stats:\n"
        f"Invited Users: {invite_count}\n"
        f"Referral Link: {referral_link}\n"
        f"Invite more users to earn 25 kyat per user who joins all required channels!"
    )
    logger.info(f"Sent referral stats to user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering users and referral_users handlers")
    application.add_handler(CommandHandler("users", users))
    application.add_handler(CommandHandler("referral_users", referral_users))