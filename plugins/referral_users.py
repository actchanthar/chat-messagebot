from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def referral_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    try:
        user = await db.get_user(user_id)
        if not user:
            await update.message.reply_text("User not found. Please start with /start.")
            return

        invites = user.get("invites", [])
        invite_count = user.get("invite_count", 0)
        message = f"Your Invites: {invite_count}\n"
        if invites:
            message += "Invited Users:\n"
            for i, invitee_id in enumerate(invites, 1):
                invitee = await db.get_user(invitee_id)
                if invitee:
                    username = invitee.get("username", "N/A")
                    if username != "N/A":
                        username = f"@{username}"
                    message += f"{i}. {invitee['name']} ({username})\n"
                else:
                    message += f"{i}. User ID {invitee_id} (Not found)\n"
        else:
            message += "No users invited yet.\n"
        await update.message.reply_text(message)
        logger.info(f"User {user_id} checked referral users: {invite_count} invites, invites list: {invites}")
    except Exception as e:
        await update.message.reply_text("Failed to fetch referral users.")
        logger.error(f"Error in referral_users for user {user_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("referral_users", referral_users))