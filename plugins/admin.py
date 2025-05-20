from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import ADMIN_IDS, LOG_CHANNEL_ID
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

from database.database import db

async def dfusers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        logger.info(f"Non-admin {user_id} attempted /dfusers")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    try:
        deleted_count = await db.delete_failed_broadcast_users()
        logger.info(f"Admin {user_id} deleted {deleted_count} users with failed broadcasts")
        await update.message.reply_text(f"Successfully deleted {deleted_count} users with failed broadcasts.")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin {user_id} deleted {deleted_count} users with failed broadcasts."
        )
    except Exception as e:
        logger.error(f"Error deleting failed broadcast users by {user_id}: {e}")
        await update.message.reply_text("Error deleting users. Please try again later.")

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        top_users = await db.get_top_users_by_invites(limit=10)
        if not top_users:
            await update.message.reply_text("No users found.")
            return

        reward_text = await db.get_phone_bill_reward_text()
        message = f"🏆 Top Users by Invites ({reward_text}):\n\n"
        for i, user in enumerate(top_users, 1):
            username = user.get("username", user.get("name", "Unknown"))
            invites = user.get("invited_users", 0)
            message += f"{i}. @{username} - {invites} invites\n"

        await update.message.reply_text(message)
        logger.info(f"Top users displayed for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error processing /top for user {update.effective_user.id}: {e}")
        await update.message.reply_text("Error retrieving top users. Please try again later.")

async def set_phone_bill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        logger.info(f"Non-admin {user_id} attempted /SetPhoneBill")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Please provide a reward text. Usage: /SetPhoneBill <text>")
        return

    reward_text = " ".join(context.args)
    try:
        await db.set_phone_bill_reward_text(reward_text)
        logger.info(f"Admin {user_id} set Phone Bill reward text to: {reward_text}")
        await update.message.reply_text(f"Phone Bill reward text set to: {reward_text}")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin {user_id} set Phone Bill reward text to: {reward_text}"
        )
    except Exception as e:
        logger.error(f"Error setting Phone Bill reward text by {user_id}: {e}")
        await update.message.reply_text("Error setting reward text. Please try again later.")

def register_handlers(application: Application):
    logger.info("Registering admin handlers")
    application.add_handler(CommandHandler("dfusers", dfusers))
    application.add_handler(CommandHandler("top", top))
    application.add_handler(CommandHandler("SetPhoneBill", set_phone_bill))