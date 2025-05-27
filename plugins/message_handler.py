from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters, ConversationHandler
from database.database import db
import logging
from config import COUNT_MESSAGES

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message_text = update.message.text or update.message.caption or ""
    logger.info(f"Message received from user {user_id} in chat {chat_id}: {message_text}")

    # Skip if in a private chat or no message text/caption
    if update.effective_chat.type == "private" or not message_text:
        logger.info(f"Skipping message in private chat or empty message for user {user_id}")
        return

    # Skip if in a conversation state (e.g., /withdraw or /rmamount)
    if context.conversation_handler and context.conversation_handler.is_running(update, context):
        logger.info(f"Skipping message during active conversation for user {user_id}")
        return

    if not COUNT_MESSAGES:
        logger.info(f"Message counting is disabled. Skipping update in chat {chat_id}.")
        return

    if chat_id != "-1002061898677":
        logger.info(f"Chat {chat_id} is not the target group (-1002061898677). Skipping update.")
        return

    if await db.check_rate_limit(user_id, message_text):
        logger.warning(f"Rate limit or duplicate enforced for user {user_id} in chat {chat_id}")
        return

    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name)

    message_rate = await db.get_message_rate()  # Get current message rate (default 3 messages = 1 kyat)
    new_messages = user.get("messages", 0) + 1
    group_messages = user.get("group_messages", {})
    current_group_messages = group_messages.get(chat_id, 0) + 1
    group_messages[chat_id] = current_group_messages
    new_balance = user.get("balance", 0) + (1 / message_rate)  # Increment balance by 1/message_rate kyat

    await db.update_user(user_id, {
        "messages": new_messages,
        "balance": new_balance,
        "group_messages": group_messages
    })
    logger.info(f"Updated messages to {new_messages} and balance to {new_balance} for user {user_id} in group {chat_id}")

def register_handlers(application: Application):
    logger.info("Registering message handlers")
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
        group=2  # Lower priority to avoid interfering with conversation handlers
    )
    application.add_handler(
        MessageHandler(filters.CAPTION & ~filters.COMMAND, handle_message),
        group=2  # Lower priority to avoid interfering with conversation handlers
    )