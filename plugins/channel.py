from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
from config import ADMIN_IDS
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /addchnl <channel_id> <channel_username>")
        return

    channel_id, channel_username = args[0], args[1]
    try:
        channel_id = str(int(channel_id))  # Ensure channel_id is numeric
        if not channel_username.startswith("@"):
            channel_username = f"@{channel_username}"
        await db.add_channel(channel_id, channel_username)
        await update.message.reply_text(f"Channel {channel_username} ({channel_id}) added successfully.")
        logger.info(f"Channel {channel_id} added by admin {user_id}")
    except ValueError:
        await update.message.reply_text("Invalid channel ID. Please provide a numeric ID (e.g., -1001234567890).")
    except Exception as e:
        logger.error(f"Error adding channel {channel_id}: {e}")
        await update.message.reply_text("Error adding channel. Please try again.")

async def delete_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /delchnl <channel_id>")
        return

    channel_id = args[0]
    try:
        channel_id = str(int(channel_id))
        success = await db.delete_channel(channel_id)
        if success:
            await update.message.reply_text(f"Channel {channel_id} deleted successfully.")
            logger.info(f"Channel {channel_id} deleted by admin {user_id}")
        else:
            await update.message.reply_text("Channel not found.")
    except ValueError:
        await update.message.reply_text("Invalid channel ID. Please provide a numeric ID.")
    except Exception as e:
        logger.error(f"Error deleting channel {channel_id}: {e}")
        await update.message.reply_text("Error deleting channel. Please try again.")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    channels = await db.get_channels()
    if not channels:
        await update.message.reply_text("No channels found.")
        return

    message = "Registered Channels:\n"
    for channel in channels:
        message += f"- {channel['name']} ({channel['chat_id']})\n"
    await update.message.reply_text(message)
    logger.info(f"Listed channels for admin {user_id}")

def register_handlers(application: Application):
    logger.info("Registering channel handlers")
    application.add_handler(CommandHandler("addchnl", add_channel))
    application.add_handler(CommandHandler("delchnl", delete_channel))
    application.add_handler(CommandHandler("listchnl", list_channels))