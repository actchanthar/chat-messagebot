from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addchnl <channel_id> <channel_name>")
        return

    channel_id, channel_name = context.args[0], " ".join(context.args[1:])
    result = await db.add_channel(channel_id, channel_name)
    if result == "exists":
        await update.message.reply_text(f"Channel {channel_name} ({channel_id}) is already added.")
    elif result:
        await update.message.reply_text(f"Added channel {channel_name} ({channel_id}) for force-subscription.")
        await context.bot.send_message(LOG_CHANNEL_ID, f"Admin added channel {channel_name} ({channel_id}).")
    else:
        await update.message.reply_text("Failed to add channel. Please try again.")

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /delchnl <channel_id>")
        return

    channel_id = context.args[0]
    if await db.remove_channel(channel_id):
        await update.message.reply_text(f"Removed channel {channel_id} from force-subscription.")
        await context.bot.send_message(LOG_CHANNEL_ID, f"Admin removed channel {channel_id}.")
    else:
        await update.message.reply_text(f"Channel {channel_id} not found or failed to remove.")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    channels = await db.get_channels()
    if not channels:
        await update.message.reply_text("No force-subscription channels added.")
        return

    message = "Force-Subscription Channels:\n"
    for channel in channels:
        message += f"{channel['name']} ({channel['channel_id']})\n"
    await update.message.reply_text(message)

def register_handlers(application):
    logger.info("Registering channel management handlers")
    application.add_handler(CommandHandler("addchnl", add_channel))
    application.add_handler(CommandHandler("delchnl", remove_channel))
    application.add_handler(CommandHandler("listchnl", list_channels))