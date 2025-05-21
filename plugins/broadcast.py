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
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized.")
        return

    try:
        if not context.args:
            await update.message.reply_text("Usage: /broadcast <message>")
            return

        message = " ".join(context.args)
        users = await db.get_all_users()
        if not users:
            await update.message.reply_text("No users to broadcast to.")
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
                if sent_count % 30 == 0:
                    await asyncio.sleep(1)
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Failed to send broadcast to {user['user_id']}: {e}")
                failed_count += 1

        await update.message.reply_text(
            f"Broadcast complete: Sent to {sent_count} users, failed for {failed_count} users."
        )
    except Exception as e:
        logger.error(f"Error in broadcast for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text("An error occurred during broadcast.")

def register_handlers(application: Application):
    logger.info("Registering broadcast handlers")
    application.add_handler(CommandHandler("broadcast", broadcast, block=False))