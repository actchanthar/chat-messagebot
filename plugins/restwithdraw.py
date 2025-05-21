from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def restwithdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /restwithdraw <user_id> or /restwithdraw ALL")
        return

    target = context.args[0]
    if target.upper() == "ALL":
        if await db.reset_withdrawals():
            await update.message.reply_text("Reset withdrawal limits for all users.")
            await context.bot.send_message(LOG_CHANNEL_ID, "Admin reset withdrawal limits for all users.")
        else:
            await update.message.reply_text("Failed to reset withdrawal limits.")
    else:
        if await db.reset_withdrawals(target):
            await update.message.reply_text(f"Reset withdrawal limits for user {target}.")
            await context.bot.send_message(LOG_CHANNEL_ID, f"Admin reset withdrawal limits for user {target}.")
        else:
            await update.message.reply_text(f"Failed to reset withdrawal limits for user {target}.")

def register_handlers(application):
    logger.info("Registering restwithdraw handlers")
    application.add_handler(CommandHandler("restwithdraw", restwithdraw))