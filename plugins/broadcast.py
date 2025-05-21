from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import ADMIN_IDS, LOG_CHANNEL_ID
from database.database import db
import logging
import asyncio

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"/broadcast command initiated by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Only admins can broadcast messages.")
        logger.info(f"User {user_id} attempted /broadcast but is not an admin")
        return

    if not context.args:
        await update.message.reply_text("Please provide a message to broadcast. Usage: /broadcast <message>")
        logger.info(f"User {user_id} provided no message for /broadcast")
        return

    message = " ".join(context.args)
    users = db.get_all_users()
    total_users = len(users)
    success_count = 0
    failed_count = 0

    for user in users:
        user_id = user["user_id"]
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            success_count += 1
            logger.info(f"Sent broadcast to user {user_id}")
            await asyncio.sleep(0.05)  # Avoid rate limits
        except Exception as e:
            logger.error(f"Failed to send broadcast to user {user_id}: {e}")
            db.mark_broadcast_failure(user_id)
            failed_count += 1

    summary = (
        f"Broadcast completed:\n"
        f"Total users: {total_users}\n"
        f"Sent successfully to: {success_count} users\n"
        f"Failed for: {failed_count} users"
    )
    try:
        await update.message.reply_text(summary)
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=summary)
        logger.info(f"Broadcast summary sent to user {user_id} and log channel {LOG_CHANNEL_ID}")
    except Exception as e:
        logger.error(f"Failed to send broadcast summary to user {user_id}: {e}")
        try:
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Failed to send broadcast summary to {user_id}: {e}"
            )
        except Exception as log_error:
            logger.error(f"Failed to log broadcast error to {LOG_CHANNEL_ID}: {log_error}")

def register_handlers(application: Application):
    logger.info("Registering broadcast handlers")
    application.add_handler(CommandHandler("broadcast", broadcast))