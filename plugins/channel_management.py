from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def addchnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addchnl <channel_id> <channel_name>")
        return

    channel_id, channel_name = context.args[0], " ".join(context.args[1:])
    result = await db.add_channel(channel_id, channel_name)
    if result == "exists":
        await update.message.reply_text(f"Channel {channel_id} is already added.")
    elif result:
        await update.message.reply_text(f"Added channel {channel_name} ({channel_id}) for forced subscription.")
        await context.bot.send_message(LOG_CHANNEL_ID, f"Admin added channel {channel_name} ({channel_id}).")
    else:
        await update.message.reply_text("Failed to add channel.")

async def delchnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /delchnl <channel_id>")
        return

    channel_id = context.args[0]
    if await db.remove_channel(channel_id):
        await update.message.reply_text(f"Removed channel {channel_id}.")
        await context.bot.send_message(LOG_CHANNEL_ID, f"Admin removed channel {channel_id}.")
    else:
        await update.message.reply_text(f"Channel {channel_id} not found.")

async def listchnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    channels = await db.get_channels()
    if not channels:
        await update.message.reply_text("No channels added for forced subscription.")
        return

    message = "Force-Subscribe Channels:\n"
    for channel in channels:
        message += f"{channel['name']} - {channel['channel_id']}\n"
    await update.message.reply_text(message)

async def checksubscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    channels = await db.get_channels()
    if not channels:
        await update.message.reply_text("No channels set for subscription.")
        return

    not_joined = []
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(channel["channel_id"], int(user_id))
            if member.status not in ["member", "administrator", "creator"]:
                not_joined.append(f"{channel['name']} ({channel['channel_id']})")
        except Exception:
            not_joined.append(f"{channel['name']} ({channel['channel_id']})")

    if not_joined:
        await update.message.reply_text(f"Please join the following channels:\n" + "\n".join(not_joined))
    else:
        await update.message.reply_text("You have joined all required channels!")

def register_handlers(application: Application):
    logger.info("Registering channel management handlers")
    application.add_handler(CommandHandler("addchnl", addchnl))
    application.add_handler(CommandHandler("delchnl", delchnl))
    application.add_handler(CommandHandler("listchnl", listchnl))
    application.add_handler(CommandHandler("checksubscription", checksubscription))