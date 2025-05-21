from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import BOT_USERNAME, REQUIRED_CHANNELS
import asyncio
import telegram.error

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    inviter_id = context.args[0].replace("referral_", "") if context.args and context.args[0].startswith("referral_") else None
    logger.info(f"Start command by user {user_id} in chat {chat_id}, inviter: {inviter_id}")

    try:
        user = await db.get_user(user_id)
        if not user:
            for attempt in range(3):
                user = await db.create_user(user_id, update.effective_user.full_name or "Unknown", inviter_id)
                if user:
                    break
                logger.warning(f"Attempt {attempt + 1} failed to create user {user_id}")
                await asyncio.sleep(0.5)
            if not user:
                logger.error(f"Failed to create user {user_id} after 3 attempts")
                try:
                    await update.message.reply_text("Error creating user. Please try again or contact @actearnbot.")
                except telegram.error.TelegramError as e:
                    logger.error(f"Failed to send error message to {user_id}: {e}")
                return

        await db.update_user(user_id, {"username": update.effective_user.username})

        referral_link = f"https://t.me/{BOT_USERNAME}?start=referral_{user_id}"
        welcome_message = (
            f"Welcome to the Chat Bot, {update.effective_user.full_name or 'User'}! 🎉\n\n"
            "⚠️ Join our channel to use this bot:\n"
            f"https://t.me/{REQUIRED_CHANNELS[0].lstrip('@')}\n\n"
            "Earn money by sending messages in our group!\n"
            f"Your referral link: {referral_link}\n"
            "Invite friends to earn 25 kyats per join (they get 50 kyats).\n"
            "Join our channel and use /checksubscription to unlock withdrawals."
        )

        keyboard = [
            [InlineKeyboardButton("Join Channel", url=f"https://t.me/{REQUIRED_CHANNELS[0].lstrip('@')}")],
            [
                InlineKeyboardButton("Check Balance", callback_data="balance"),
                InlineKeyboardButton("Withdraw", callback_data="withdraw")
            ],
            [InlineKeyboardButton("Join Group", url="https://t.me/yourgroup")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="HTML")
            logger.info(f"Sent welcome message to user {user_id}")
            await asyncio.sleep(0.2)  # Rate limit delay
        except telegram.error.TelegramError as e:
            logger.error(f"Failed to send welcome message to {user_id}: {e}", exc_info=True)
            try:
                await update.message.reply_text("An error occurred. Please try again or contact @actearnbot.")
            except telegram.error.TelegramError as e2:
                logger.error(f"Failed to send error message to {user_id}: {e2}")
    except Exception as e:
        logger.error(f"Error in start for user {user_id}: {e}", exc_info=True)
        try:
            await update.message.reply_text("An error occurred. Please try again or contact @actearnbot.")
        except telegram.error.TelegramError as e2:
            logger.error(f"Failed to send error message to {user_id}: {e2}")

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start, block=False))