from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
from database.database import db
import logging
from config import GROUP_CHAT_IDS, COUNT_MESSAGES, CURRENCY
from datetime import datetime, timedelta
from collections import defaultdict

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting: max 5 messages per user per minute
RATE_LIMIT = 5
RATE_LIMIT_WINDOW = timedelta(minutes=1)
user_message_timestamps = defaultdict(list)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not COUNT_MESSAGES:
        logger.info("Message counting disabled")
        return

    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    current_time = datetime.utcnow()

    # Rate limiting
    user_timestamps = user_message_timestamps[user_id]
    user_timestamps = [t for t in user_timestamps if current_time - t < RATE_LIMIT_WINDOW]
    user_timestamps.append(current_time)
    user_message_timestamps[user_id] = user_timestamps

    if len(user_timestamps) > RATE_LIMIT:
        logger.info(f"User {user_id} rate limited: {len(user_timestamps)} messages")
        return

    logger.info(f"Processing message from user {user_id} in chat {chat_id}")

    if chat_id not in GROUP_CHAT_IDS:
        logger.debug(f"Ignoring message in chat {chat_id}. Expected: {GROUP_CHAT_IDS}")
        return

    user = await db.get_user(user_id)
    if not user:
        logger.info(f"Creating user {user_id}")
        user = await db.create_user(user_id, update.effective_user.full_name, None)
        if not user:
            logger.error(f"Failed to create user {user_id}")
            return

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned")
        return

    group_messages = user.get("group_messages", {})
    group_messages[chat_id] = group_messages.get(chat_id, 0) + 1
    total_messages = user.get("messages", 0) + 1
    balance = total_messages  # 1 message = 1 kyat

    try:
        await db.update_user(user_id, {
            "messages": total_messages,
            "group_messages": group_messages,
            "balance": balance
        })
        logger.info(f"Updated user {user_id}: messages={total_messages}, balance={balance} {CURRENCY}")
    except Exception as e:
        logger.error(f"Failed to update user {user_id}: {str(e)}")

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    logger.info(f"Chat ID requested: {chat_id}")
    await update.message.reply_text(f"Chat ID: {chat_id}")

async def reset_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in context.bot_data.get("admin_ids", []):
        await update.message.reply_text("You are not authorized.")
        return
    target_id = context.args[0] if context.args else user_id
    if await db.reset_user_messages(target_id):
        await update.message.reply_text(f"Messages reset for user {target_id}.")
    else:
        await update.message.reply_text(f"Failed to reset messages for user {target_id}.")

async def debug_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Debug message command by user {user_id} in chat {chat_id}")
    await update.message.reply_text(
        f"Chat ID: {chat_id}\n"
        f"Expected GROUP_CHAT_IDS: {GROUP_CHAT_IDS}\n"
        f"Message counting enabled: {COUNT_MESSAGES}"
    )

def register_handlers(application: Application):
    logger.info("Registering message handler")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Chat(GROUP_CHAT_IDS), handle_message))
    application.add_handler(CommandHandler("getchatid", get_chat_id))
    application.add_handler(CommandHandler("resetmessages", reset_messages))
    application.add_handler(CommandHandler("debugmessage", debug_message))