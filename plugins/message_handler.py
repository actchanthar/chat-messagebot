import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from database.database import db
from config import GROUP_CHAT_IDS, CURRENCY, LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat or chat.type not in ["group", "supergroup"]:
        logger.debug(f"Ignoring message: user={user}, chat_type={chat.type if chat else None}")
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
            if not db_user:
                logger.error(f"Failed to create or retrieve user {user_id}")
                await message.reply_text("Error processing your account. Please try again later.")
                return

        # Initialize group_messages if missing
        if chat_id not in db_user.get("group_messages", {}):
            await db.update_user(user_id, {f"group_messages.{chat_id}": 0})

        # Check rate limit (5 messages per minute)
        if await db.check_rate_limit(user_id):
            await message.reply_text("You are sending messages too quickly. Please wait a minute.")
            try:
                await context.bot.send_message(
                    chat_id=LOG_CHANNEL_ID,
                    text=f"User {user_id} hit rate limit in group {chat_id}"
                )
            except Exception as e:
                logger.warning(f"Failed to notify log channel {LOG_CHANNEL_ID}: {e}")
            return

        # Increment message count
        if not await db.increment_messages(user_id, chat_id):
            logger.error(f"Failed to increment messages for user {user_id} in group {chat_id}")
            await message.reply_text("Error counting your message. Please try again.")
            return
        logger.info(f"Incremented message count for user {user_id} in group {chat_id}")

        # Check if user earned currency
        messages_per_kyat = await db.get_message_rate() or 3
        user = await db.get_user(user_id)
        if not user:
            logger.error(f"User {user_id} not found after increment")
            await message.reply_text("Error retrieving your account. Please try again.")
            return

        group_messages = user["group_messages"].get(chat_id, 0)
        if group_messages > 0 and group_messages % messages_per_kyat == 0:
            earned = 1.0
            if not await db.update_balance(user_id, earned):
                logger.error(f"Failed to update balance for user {user_id}")
                await message.reply_text("Error updating your balance. Please try again.")
                return
            user = await db.get_user(user_id)
            balance = user["balance"]
            await message.reply_text(
                f"🎉 You earned {earned} {CURRENCY}!\n"
                f"Your new balance: {balance} {CURRENCY}"
            )
            try:
                await context.bot.send_message(
                    chat_id=LOG_CHANNEL_ID,
                    text=f"User {user_id} earned {earned} {CURRENCY} in group {chat_id}. New balance: {balance}"
                )
            except Exception as e:
                logger.warning(f"Failed to notify log channel {LOG_CHANNEL_ID}: {e}")
            logger.info(f"User {user_id} earned {earned} {CURRENCY} in group {chat_id}")

        # Notify at 10 kyat
        if user["balance"] >= 10 and not user.get("notified_10kyat", False):
            await message.reply_text(
                f"🎉 Your balance is {user['balance']} {CURRENCY}! "
                f"You can now withdraw using /withdraw."
            )
            if not await db.update_user(user_id, {"notified_10kyat": True}):
                logger.warning(f"Failed to set notified_10kyat for user {user_id}")
            try:
                await context.bot.send_message(
                    chat_id=LOG_CHANNEL_ID,
                    text=f"User {user_id} notified of 10 {CURRENCY} balance in group {chat_id}"
                )
            except Exception as e:
                logger.warning(f"Failed to notify log channel {LOG_CHANNEL_ID}: {e}")

    except Exception as e:
        logger.error(f"Error processing message for user {user_id} in group {chat_id}: {e}", exc_info=True)
        await message.reply_text("An error occurred while processing your message. Please try again.")
        try:
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Error processing message for user {user_id} in group {chat_id}: {e}"
            )
        except Exception as e:
            logger.warning(f"Failed to notify log channel {LOG_CHANNEL_ID}: {e}")

def register_handlers(application: Application):
    logger.info("Registering message handler")
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
            handle_message
        ),
        group=2
    )