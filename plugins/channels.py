from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def addchnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Addchnl command initiated by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized addchnl attempt by user {user_id}")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Please provide a channel ID and name. Usage: /addchnl <channel_id> <channel_name>")
        logger.info(f"Insufficient arguments provided by user {user_id}")
        return

    channel_id = context.args[0]
    channel_name = " ".join(context.args[1:])
    if not channel_id.startswith("-100"):
        await update.message.reply_text("Invalid channel ID. It should start with -100 (e.g., -1001916718471).")
        logger.info(f"Invalid channel ID {channel_id} provided by user {user_id}")
        return

    result = await db.add_channel(channel_id, channel_name)
    if result == "exists":
        await update.message.reply_text(f"Channel {channel_name} ({channel_id}) is already added.")
        logger.info(f"Channel {channel_id} already exists, no action taken by admin {user_id}")
    elif result:
        await update.message.reply_text(f"Channel {channel_name} ({channel_id}) has been added for force subscription.")
        logger.info(f"Channel {channel_id} added by admin {user_id}")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin added channel {channel_name} ({channel_id}) for force subscription."
        )
    else:
        await update.message.reply_text("Failed to add the channel. Please try again.")
        logger.error(f"Failed to add channel {channel_id} by user {user_id}")

async def delchnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Delchnl command initiated by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized delchnl attempt by user {user_id}")
        return

    if not context.args:
        await update.message.reply_text("Please provide a channel ID. Usage: /delchnl <channel_id>")
        logger.info(f"No channel ID provided by user {user_id}")
        return

    channel_id = context.args[0]
    result = await db.remove_channel(channel_id)
    if result:
        await update.message.reply_text(f"Channel {channel_id} has been removed from force subscription.")
        logger.info(f"Channel {channel_id} removed by admin {user_id}")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin removed channel {channel_id} from force subscription."
        )
    else:
        await update.message.reply_text(f"Channel {channel_id} not found or failed to remove.")
        logger.info(f"Channel {channel_id} not found for removal by user {user_id}")

async def listchnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Listchnl command initiated by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized listchnl attempt by user {user_id}")
        return

    channels = await db.get_channels()
    if not channels:
        await update.message.reply_text("No channels are currently set for force subscription.")
        logger.info(f"No channels found for user {user_id}")
        return

    message = "Force Subscription Channels:\n"
    for channel in channels:
        message += f"{channel['channel_name']} ({channel['channel_id']})\n"
    await update.message.reply_text(message)
    logger.info(f"Sent channel list to user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering channel handlers")
    application.add_handler(CommandHandler("addchnl", addchnl))
    application.add_handler(CommandHandler("delchnl", delchnl))
    application.add_handler(CommandHandler("listchnl", listchnl))