from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import ADMIN_IDS, FORCE_SUB_CHANNELS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Add_channel command by user {user_id}")

    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized add_channel attempt by user {user_id}")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addchnl <channel_id> <channel_name>")
        logger.info(f"Insufficient arguments for add_channel by user {user_id}")
        return

    channel_id = context.args[0]
    channel_name = " ".join(context.args[1:])
    try:
        # Validate channel ID
        if not channel_id.startswith("-100"):
            await update.message.reply_text("Invalid channel ID. It should start with -100 (e.g., -1002171798406).")
            return

        # Check if bot is admin in the channel
        member = await context.bot.get_chat_member(channel_id, context.bot.id)
        if member.status not in ["administrator", "creator"]:
            await update.message.reply_text("Please make the bot an admin in the channel first.")
            return

        await db.add_channel(channel_id, channel_name)
        if channel_id not in FORCE_SUB_CHANNELS:
            FORCE_SUB_CHANNELS.append(channel_id)
        await update.message.reply_text(f"Added channel {channel_name} ({channel_id}) to force-subscription list.")
        logger.info(f"User {user_id} added channel {channel_id}: {channel_name}")
    except Exception as e:
        await update.message.reply_text("Error adding channel. Ensure the channel ID is correct and the bot is an admin.")
        logger.error(f"Error adding channel {channel_id} by user {user_id}: {e}")

async def delete_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Delete_channel command by user {user_id}")

    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized delete_channel attempt by user {user_id}")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /delchnl <channel_id>")
        logger.info(f"Insufficient arguments for delete_channel by user {user_id}")
        return

    channel_id = context.args[0]
    try:
        await db.delete_channel(channel_id)
        if channel_id in FORCE_SUB_CHANNELS:
            FORCE_SUB_CHANNELS.remove(channel_id)
        await update.message.reply_text(f"Removed channel {channel_id} from force-subscription list.")
        logger.info(f"User {user_id} deleted channel {channel_id}")
    except Exception as e:
        await update.message.reply_text("Error removing channel. Ensure the channel ID is correct.")
        logger.error(f"Error removing channel {channel_id} by user {user_id}: {e}")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"List_channels command by user {user_id}")

    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized list_channels attempt by user {user_id}")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    channels = await db.get_channels()
    if not channels:
        await update.message.reply_text("No channels in force-subscription list.")
        return

    message = "Force-Subscription Channels:\n\n"
    for channel in channels:
        message += f"Name: {channel['name']}\nID: {channel['channel_id']}\n\n"
    await update.message.reply_text(message)
    logger.info(f"User {user_id} listed channels")

def register_handlers(application: Application):
    logger.info("Registering channel handlers")
    application.add_handler(CommandHandler("addchnl", add_channel))
    application.add_handler(CommandHandler("delchnl", delete_channel))
    application.add_handler(CommandHandler("listchnl", list_channels))