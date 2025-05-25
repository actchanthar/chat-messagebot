from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def addchnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addchnl <channel_id> <channel_name>")
        return

    channel_id, *channel_name = context.args
    channel_name = " ".join(channel_name)
    if not channel_id.startswith("-100"):
        await update.message.reply_text("Invalid channel ID. Must start with -100.")
        return

    result = await db.add_channel(channel_id, channel_name)
    if result == "exists":
        await update.message.reply_text(f"Channel {channel_id} already exists.")
    elif result:
        await update.message.reply_text(f"Added channel {channel_name} ({channel_id}).")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin added channel {channel_name} ({channel_id})."
        )
    else:
        await update.message.reply_text("Failed to add channel.")

async def delchnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /delchnl <channel_id>")
        return

    channel_id = context.args[0]
    if not channel_id.startswith("-100"):
        await update.message.reply_text("Invalid channel ID. Must start with -100.")
        return

    if await db.remove_channel(channel_id):
        await update.message.reply_text(f"Removed channel {channel_id}.")
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Admin removed channel {channel_id}."
        )
    else:
        await update.message.reply_text("Channel not found or failed to remove.")

async def listchnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    channels = await db.get_channels()
    if not channels:
        await update.message.reply_text("No channels configured.")
        return

    channel_list = "\n".join([f"{c['name']} - {c['channel_id']}" for c in channels])
    await update.message.reply_text(f"Force-subscription channels:\n{channel_list}")

def register_handlers(application: Application):
    logger.info("Registering channel handlers")
    application.add_handler(CommandHandler("addchnl", addchnl))
    application.add_handler(CommandHandler("delchnl", delchnl))
    application.add_handler(CommandHandler("listchnl", listchnl))