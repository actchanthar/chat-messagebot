from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import ADMIN_USER_ID, LOG_CHANNEL_ID, FORCE_SUB_CHANNEL_LINKS, FORCE_SUB_CHANNEL_NAMES

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def addchnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"/addchnl command initiated by user {user_id} in chat {chat_id}")

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized /addchnl attempt by user {user_id}")
        return

    if not context.args or len(context.args) < 3:
        await update.message.reply_text("Usage: /addchnl <channel_id> <invite_link> <channel_name>")
        logger.info(f"Invalid arguments for /addchnl by user {user_id}")
        return

    channel_id = context.args[0]
    invite_link = context.args[1]
    channel_name = " ".join(context.args[2:])
    if not channel_id.startswith("-100"):
        await update.message.reply_text("Invalid channel ID. Must start with -100.")
        return

    current_channels = await db.get_force_sub_channels()
    if channel_id in current_channels:
        await update.message.reply_text(f"Channel {channel_id} is already in the force-subscription list.")
        return

    current_channels.append(channel_id)
    success = await db.set_force_sub_channels(current_channels)
    if success:
        FORCE_SUB_CHANNEL_LINKS[channel_id] = invite_link
        FORCE_SUB_CHANNEL_NAMES[channel_id] = channel_name
        await update.message.reply_text(f"Added channel {channel_id} ({channel_name}) to force-subscription list.")
        logger.info(f"Added channel {channel_id} by admin {user_id}")
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"Admin added force-sub channel: {channel_id} ({channel_name})")
    else:
        await update.message.reply_text("Failed to add channel. Please try again.")

def register_addchnl(application: Application):
    logger.info("Registering addchnl handlers")
    application.add_handler(CommandHandler("addchnl", addchnl))

async def delchnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"/delchnl command initiated by user {user_id} in chat {chat_id}")

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized /delchnl attempt by user {user_id}")
        return

    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Usage: /delchnl <channel_id>")
        logger.info(f"Invalid arguments for /delchnl by user {user_id}")
        return

    channel_id = context.args[0]
    current_channels = await db.get_force_sub_channels()
    if channel_id not in current_channels:
        await update.message.reply_text(f"Channel {channel_id} is not in the force-subscription list.")
        return

    current_channels.remove(channel_id)
    success = await db.set_force_sub_channels(current_channels)
    if success:
        channel_name = FORCE_SUB_CHANNEL_NAMES.get(channel_id, "Unknown Channel")
        if channel_id in FORCE_SUB_CHANNEL_LINKS:
            del FORCE_SUB_CHANNEL_LINKS[channel_id]
        if channel_id in FORCE_SUB_CHANNEL_NAMES:
            del FORCE_SUB_CHANNEL_NAMES[channel_id]
        await update.message.reply_text(f"Removed channel {channel_id} ({channel_name}) from force-subscription list.")
        logger.info(f"Removed channel {channel_id} by admin {user_id}")
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"Admin removed force-sub channel: {channel_id} ({channel_name})")
    else:
        await update.message.reply_text("Failed to remove channel. Please try again.")

def register_delchnl(application: Application):
    logger.info("Registering delchnl handlers")
    application.add_handler(CommandHandler("delchnl", delchnl))

async def listchnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"/listchnl command initiated by user {user_id} in chat {chat_id}")

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized /listchnl attempt by user {user_id}")
        return

    force_sub_channels = await db.get_force_sub_channels()
    if not force_sub_channels:
        await update.message.reply_text("No force-subscription channels configured.")
    else:
        channel_list = "\n".join([
            f"- {FORCE_SUB_CHANNEL_NAMES.get(channel_id, 'Unknown Channel')} ({channel_id}): {FORCE_SUB_CHANNEL_LINKS.get(channel_id, 'No link')}"
            for channel_id in force_sub_channels
        ])
        await update.message.reply_text(f"Force-Subscription Channels:\n{channel_list}")

def register_listchnl(application: Application):
    logger.info("Registering listchnl handlers")
    application.add_handler(CommandHandler("listchnl", listchnl))

def register_handlers(application: Application):
    register_addchnl(application)
    register_delchnl(application)
    register_listchnl(application)