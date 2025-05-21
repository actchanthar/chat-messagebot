# plugins/check_subscription.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config import REQUIRED_CHANNELS
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if user is subscribed to required channels
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Checking subscription for user {user_id}")

    user = await db.get_user(user_id)
    if not user:
        logger.error(f"User {user_id} not found in database")
        await update.message.reply_text("User not found. Please start with /start.")
        return

    subscribed_channels = user.get("subscribed_channels", [])
    missing_channels = [ch for ch in REQUIRED_CHANNELS if ch not in subscribed_channels]

    if missing_channels:
        logger.info(f"User {user_id} is missing subscriptions to: {missing_channels}")
        response = "You need to join the following channels to use this bot:\n"
        buttons = []

        for channel in missing_channels:
            try:
                chat = await context.bot.get_chat(channel)
                invite_link = await context.bot.export_chat_invite_link(channel)
                response += f"- {chat.title}: {invite_link}\n"
                buttons.append([InlineKeyboardButton(f"Join {chat.title}", url=invite_link)])
            except Exception as e:
                logger.error(f"Failed to get invite link for {channel}: {e}")
                # Fallback to a basic link if invite link generation fails
                channel_link = f"https://t.me/{channel.replace('-100', '')}"
                response += f"- Channel {channel}: {channel_link}\n"
                buttons.append([InlineKeyboardButton(f"Join Channel {channel}", url=channel_link)])

        reply_markup = InlineKeyboardMarkup(buttons)
        response += "Please join and use /start again."
        await update.message.reply_text(response, reply_markup=reply_markup)
    else:
        logger.info(f"User {user_id} has subscribed to all required channels")
        await update.message.reply_text("Subscription verified. You can now use the bot.")

def register_handlers(application: Application):
    logger.info("Registering check_subscription handlers")
    # Register the check_subscription handler for /start and any message
    application.add_handler(CommandHandler("start", check_subscription))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, check_subscription))