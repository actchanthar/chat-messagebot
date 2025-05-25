from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from database.database import db
import logging
from config import COUNT_MESSAGES, GROUP_CHAT_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message_text = update.message.text or update.message.caption or ""
    if not message_text:
        logger.info(f"Ignored empty message from user {user_id} in chat {chat_id}")
        return

    if await db.check_rate_limit(user_id, message_text):
        logger.warning(f"Rate limit or duplicate enforced for user {user_id} in chat {chat_id}")
        return

    if not COUNT_MESSAGES:
        logger.info(f"Message counting disabled. Skipping update in chat {chat_id}.")
        return

    if chat_id not in GROUP_CHAT_IDS:
        logger.info(f"Chat {chat_id} not in target groups {GROUP_CHAT_IDS}. Skipping.")
        return

    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name)

    message_rate = await db.get_message_rate()
    new_messages = user.get("messages", 0) + 1
    group_messages = user.get("group_messages", {})
    current_group_messages = group_messages.get(chat_id, 0) + 1
    group_messages[chat_id] = current_group_messages
    new_balance = user.get("balance", 0) + (1 / message_rate if new_messages % message_rate == 0 else 0)

    await db.update_user(user_id, {
        "messages": new_messages,
        "balance": new_balance,
        "group_messages": group_messages,
        "last_activity": datetime.utcnow()
    })
    logger.info(f"Updated user {user_id}: messages={new_messages}, balance={new_balance}, group_messages={group_messages}")

def register_handlers(application: Application):
    logger.info("Registering message handlers")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.CAPTION & ~filters.COMMAND, handle_message))