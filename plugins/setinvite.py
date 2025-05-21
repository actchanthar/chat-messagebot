from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def setinvite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setinvite <number_of_invites>")
        return

    try:
        invites_needed = int(context.args[0])
        if invites_needed < 0:
            await update.message.reply_text("Invite requirement must be non-negative.")
            return
        if await db.set_invite_requirement(invites_needed):
            await update.message.reply_text(f"Invite requirement set to {invites_needed} users.")
            await context.bot.send_message(LOG_CHANNEL_ID, f"Admin set invite requirement to {invites_needed} users.")
        else:
            await update.message.reply_text("Failed to set invite requirement.")
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")

def register_handlers(application):
    logger.info("Registering setinvite handlers")
    application.add_handler(CommandHandler("setinvite", setinvite))