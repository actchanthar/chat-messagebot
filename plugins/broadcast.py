from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import ADMIN_IDS
import asyncio

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Broadcast initiated by user {user_id}")

    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized broadcast attempt by {user_id}")
        try:
            await update.message.reply_text("You are not authorized.")
        except Exception as e:
            logger.error(f"Failed to send unauthorized message to {user_id}: {e}")
        return

    try:
        if not context.args:
            logger.warning(f"No message provided for broadcast by {user_id}")
            try:
                await update.message.reply_text("Usage: /broadcast <message>")
            except Exception as e:
                logger.error(f"Failed to send usage message to {user_id}: {e}")
            return

        message = " ".join(context.args)
        users = await db.get_all_users()
        if not users:
            logger.info(f"No users found for broadcast by {user_id}")
            try:
                await update.message.reply_text("No users to broadcast to.")
            except Exception as e:
                logger.error(f"Failed to send no users message to {user_id}: {e}")
            return

        sent_count = 0
        failed_count = 0
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user["user_id"],
                    text=message,
                    parse_mode="HTML"
                )
                sent_count += 1
                logger.info(f"Sent broadcast to user {user['user_id']}")
                if sent_count % 30 == 0:
                    await asyncio.sleep(1)
                else:
                    await asyncio.sleep(0.2)  # Increased delay
            except Exception as e:
                logger.error(f"Failed to send broadcast to {user['user_id']}: {e}")
                failed_count += 1

        try:
            await update.message.reply_text(
                f"Broadcast complete: Sent to {sent_count} users, failed for {failed_count} users."
            )
            logger.info(f"Broadcast by {user_id} completed: {sent_count} successes, {failed_count} failures")
        except Exception as e:
            logger.error(f"Failed to send broadcast summary to {user_id}: {e}")
    except Exception as e:
        logger.error(f"Error in broadcast for user {user_id}: {e}", exc_info=True)
        try:
            await update.message.reply_text("An error occurred during broadcast.")
        except Exception as e2:
            logger.error(f"Failed to send error message to {user_id}: {e2}")

def register_handlers(application: Application):
    logger.info("Registering broadcast handlers")
    application.add_handler(CommandHandler("broadcast", broadcast, block=False))