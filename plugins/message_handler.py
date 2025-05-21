from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from database.database import db
import logging
from config import COUNT_MESSAGES

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message_text = update.message.text
    logger.info(f"Message from user {user_id} in chat {chat_id}: {message_text}")

    if await db.check_rate_limit(user_id, message_text):
        logger.warning(f"Rate limit or duplicate for user {user_id}")
        return

    if not await db.is_message_counting_enabled():
        logger.info(f"Message counting disabled. Skipping update in chat {chat_id}.")
        return

    if chat_id != "-1002061898677":
        logger.info(f"Chat {chat_id} is not target group (-1002061898677).")
        return

    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name)

    group_messages = user.get("group_messages", {})
    current_group_messages = group_messages.get(chat_id, 0) + 1
    group_messages[chat_id] = current_group_messages
    total_messages = user.get("messages", 0) + 1
    messages_per_kyat = await db.get_message_rate()
    new_balance = user.get("balance", 0) + (1 / messages_per_kyat if current_group_messages % messages_per_kyat == 0 else 0)

    await db.update_user(user_id, {
        "messages": total_messages,
        "balance": new_balance,
        "group_messages": group_messages
    })
    logger.info(f"Updated user {user_id}: messages={total_messages}, balance={new_balance}")
    if new_balance >= 10 and not user.get("notified_10kyat", False):
        for group_id in GROUP_CHAT_IDS:
            await context.bot.send_message(
                chat_id=group_id,
                text=f"{update.effective_user.full_name} has reached 10 {CURRENCY}!"
            )
        await db.update_user(user_id, {"notified_10kyat": True})

def register_handlers(application: Application):
    logger.info("Registering message handlers")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))