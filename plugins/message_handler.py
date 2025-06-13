from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
from database.database import db
import logging
from config import GROUP_CHAT_IDS, CURRENCY

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message_text = update.message.text if update.message.text else ""

    # Only process messages from approved group
    if chat_id != "-1002061898677":
        logger.debug(f"Message from user {user_id} ignored in unapproved chat {chat_id}")
        return

    try:
        user = await db.get_user(user_id)
        if not user:
            user = await db.create_user(user_id, {
                "first_name": update.effective_user.first_name,
                "last_name": update.effective_user.last_name
            })
            if not user:
                logger.error(f"Failed to create user {user_id} in handle_message")
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Error processing your account. Please try again later or contact support."
                    )
                except TelegramError as te:
                    logger.error(f"Failed to send error message to chat {chat_id}: {te}")
                return  # Skip further processing to prevent repeated errors

        if user.get("banned", False):
            logger.info(f"Banned user {user_id} attempted to send a message in chat {chat_id}")
            return

        rate_limited = await db.check_rate_limit(user_id, message_text)
        if rate_limited:
            logger.info(f"User {user_id} is rate limited in chat {chat_id}")
            return

        success = await db.increment_message_count(user_id)
        if not success:
            logger.error(f"Failed to increment message count for user {user_id}")
            return

        message_rate = await db.get_message_rate()
        new_messages = user.get("messages", 0) + 1
        if new_messages % message_rate == 0:
            current_balance = user.get("balance", 0)
            new_balance = current_balance + 1
            success = await db.update_user(user_id, {"balance": new_balance})
            if success:
                logger.info(f"User {user_id} earned 1 {CURRENCY}, new balance: {new_balance}")
                if new_balance == 10 and not user.get("notified_10kyat", False):
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"🎉 ဂုဏ်ယူပါတယ်! သင့်လက်ကျန်ငွေ ၁၀ {CURRENCY} ရှိပြီဖြစ်ပါတယ်။ /withdraw ဖြင့် ငွေထုတ်နိုင်ပါပြီ။"
                        )
                        await db.update_user(user_id, {"notified_10kyat": True})
                        logger.info(f"Notified user {user_id} of 10 {CURRENCY} milestone")
                    except TelegramError as te:
                        logger.error(f"Failed to notify user {user_id} of 10 {CURRENCY} milestone: {te}")

    except TelegramError as te:
        logger.error(f"Telegram API error handling message for user {user_id} in chat {chat_id}: {te}")
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Error processing your account. Please try again later or contact support."
            )
        except TelegramError as te2:
            logger.error(f"Failed to send error message to chat {chat_id}: {te2}")
    except Exception as e:
        logger.error(f"Unexpected error handling message for user {user_id} in chat {chat_id}: {e}")
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Error processing your account. Please try again later or contact support."
            )
        except TelegramError as te:
            logger.error(f"Failed to send error message to chat {chat_id}: {te}")

def register_handlers(application: Application):
    logger.info("Registering message handlers")
    application.add_handler(
        MessageHandler(
            filters.Chat(chat_id=[int(gid) for gid in GROUP_CHAT_IDS]) & filters.TEXT & ~filters.COMMAND,
            handle_message
        ),
        group=2
    )