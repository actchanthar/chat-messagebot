from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def pbroadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /pbroadcast <message>")
        return

    message = " ".join(context.args)
    users = await db.get_all_users()
    if not users:
        await update.message.reply_text("No users found to broadcast to.")
        return

    success_count = 0
    failure_count = 0
    for user in users:
        try:
            msg = await context.bot.send_message(
                chat_id=user["user_id"],
                text=message,
                parse_mode="HTML"
            )
            await context.bot.pin_chat_message(
                chat_id=user["user_id"],
                message_id=msg.message_id,
                disable_notification=True
            )
            success_count += 1
        except Exception as e:
            failure_count += 1
            logger.error(f"Failed to broadcast to user {user['user_id']}: {e}")

    result_message = f"Pinned broadcast sent to {success_count} users, failed for {failure_count} users."
    await update.message.reply_text(result_message)
    await context.bot.send_message(
        LOG_CHANNEL_ID,
        f"Admin pinned broadcast: {message}\n{result_message}"
    )

def register_handlers(application):
    logger.info("Registering pbroadcast handlers")
    application.add_handler(CommandHandler("pbroadcast", pbroadcast))