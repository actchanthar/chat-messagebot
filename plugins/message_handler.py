import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from database.database import db
from config import GROUP_CHAT_IDS, CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat or chat.type not in ["group", "supergroup"]:
        return

    user_id = str(user.id)
    chat_id = str(chat.id)

    if chat_id not in GROUP_CHAT_IDS:
        logger.debug(f"Message in non-approved group {chat_id} by user {user_id}")
        return

    try:
        # Check if user exists, create if not
        db_user = await db.get_user(user_id)
        if not db_user:
            await db.create_user(user_id, {
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "username": user.username or ""
            })
            db_user = await db.get_user(user_id)

        # Initialize group_messages if missing
        if chat_id not in db_user.get("group_messages", {}):
            await db.update_user(user_id, {f"group_messages.{chat_id}": 0})

        # Check rate limit (5 messages per minute)
        if await db.check_rate_limit(user_id):
            await message.reply_text("You are sending messages too quickly. Please wait a minute.")
            return

        # Increment message count
        await db.increment_messages(user_id, chat_id)
        logger.info(f"Incremented message count for user {user_id} in group {chat_id}")

        # Check if user earned a kyat
        messages_per_kyat = await db.get_message_rate() or 3
        user = await db.get_user(user_id)
        group_messages = user["group_messages"].get(chat_id, 0)

        if group_messages > 0 and group_messages % messages_per_kyat == 0:
            earned = 1
            await db.update_balance(user_id, earned)
            user = await db.get_user(user_id)
            balance = user["balance"]
            await message.reply_text(
                f"🎉 You earned {earned} {CURRENCY}!\n"
                f"Your new balance: {balance} {CURRENCY}"
            )
            logger.info(f"User {user_id} earned {earned} {CURRENCY} in group {chat_id}")

        # Notify at 10 kyat
        if user["balance"] >= 10 and not user.get("notified_10kyat", False):
            await message.reply_text(
                f"🎉 Your balance is {user['balance']} {CURRENCY}! "
                f"You can now withdraw using /withdraw."
            )
            await db.update_user(user_id, {"notified_10kyat": True})

    except Exception as e:
        logger.error(f"Error processing message for user {user_id} in group {chat_id}: {str(e)}")
        await message.reply_text("An error occurred while processing your message. Please try again.")

def register_handlers(application: Application):
    logger.info("Registering message handler")
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
            handle_message
        ),
        group=2
    )