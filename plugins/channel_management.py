# plugins/channel_management.py
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    filters,
)
from config import ADMIN_IDS
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Add a channel to user's subscribed_channels
async def addchnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"/addchnl called by user {user_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("This command is restricted to admins only.")
        return

    if not context.args:
        await update.message.reply_text("Please provide a channel ID (e.g., /addchnl -1001234567890).")
        return

    channel_id = context.args[0]
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found.")
        return

    subscribed_channels = user.get("subscribed_channels", [])
    if channel_id in subscribed_channels:
        await update.message.reply_text(f"Channel {channel_id} is already subscribed.")
        return

    subscribed_channels.append(channel_id)
    result = await db.update_user(user_id, {"subscribed_channels": subscribed_channels})
    logger.info(f"db.update_user returned: {result} for user {user_id}")

    if result and (isinstance(result, bool) or (hasattr(result, 'modified_count') and result.modified_count > 0)):
        await update.message.reply_text(f"Added channel {channel_id} to subscribed channels.")
    else:
        await update.message.reply_text("Error adding channel. Please try again.")

# Delete a channel from user's subscribed_channels
async def delchnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"/delchnl called by user {user_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("This command is restricted to admins only.")
        return

    if not context.args:
        await update.message.reply_text("Please provide a channel ID (e.g., /delchnl -1001234567890).")
        return

    channel_id = context.args[0]
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found.")
        return

    subscribed_channels = user.get("subscribed_channels", [])
    if channel_id not in subscribed_channels:
        await update.message.reply_text(f"Channel {channel_id} is not subscribed.")
        return

    subscribed_channels.remove(channel_id)
    result = await db.update_user(user_id, {"subscribed_channels": subscribed_channels})
    logger.info(f"db.update_user returned: {result} for user {user_id}")

    if result and (isinstance(result, bool) or (hasattr(result, 'modified_count') and result.modified_count > 0)):
        await update.message.reply_text(f"Removed channel {channel_id} from subscribed channels.")
    else:
        await update.message.reply_text("Error removing channel. Please try again.")

# List subscribed channels
async def listchnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"/listchnl called by user {user_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("This command is restricted to admins only.")
        return

    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found.")
        return

    subscribed_channels = user.get("subscribed_channels", [])
    if not subscribed_channels:
        await update.message.reply_text("No subscribed channels.")
    else:
        response = "Subscribed channels:\n" + "\n".join(subscribed_channels)
        await update.message.reply_text(response)

def register_handlers(application: Application):
    logger.info("Registering channel_management handlers")
    application.add_handler(CommandHandler("addchnl", addchnl, filters=filters.Command() & ~filters.CommandStart))
    application.add_handler(CommandHandler("delchnl", delchnl, filters=filters.Command() & ~filters.CommandStart))
    application.add_handler(CommandHandler("listchnl", listchnl, filters=filters.Command() & ~filters.CommandStart))