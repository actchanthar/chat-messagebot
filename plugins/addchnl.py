from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def addchnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized.")
        return

    try:
        if not context.args:
            await update.message.reply_text("Usage: /addchnl <channel_username_or_link>")
            return

        channel_id = context.args[0]
        # Validate channel_id (should be @ChannelName or https://t.me/+abc123)
        if not (channel_id.startswith('@') or channel_id.startswith('https://t.me/')):
            await update.message.reply_text("Please provide a valid channel username (e.g., @ChannelName) or invite link (e.g., https://t.me/+abc123).")
            return

        result = await db.add_required_channel(channel_id)
        if result == "exists":
            await update.message.reply_text(f"Channel {channel_id} is already in the required channels list.")
        elif result:
            await update.message.reply_text(f"Added {channel_id} to required channels. Users must now join it to withdraw.")
        else:
            await update.message.reply_text("Failed to add channel. Please try again.")
    except Exception as e:
        logger.error(f"Error in addchnl for user {user_id}: {e}")
        await update.message.reply_text("An error occurred. Please try again.")

def register_handlers(application: Application):
    logger.info("Registering addchnl handlers")
    application.add_handler(CommandHandler("addchnl", addchnl, block=False))