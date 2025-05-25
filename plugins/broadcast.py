from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import ADMIN_IDS, LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Broadcast command by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized broadcast attempt by user {user_id}")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        logger.info(f"No broadcast message provided by user {user_id}")
        await update.message.reply_text("Please provide a message to broadcast. Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    users = await db.get_all_users()
    success_count = 0
    fail_count = 0

    for user in users:
        try:
            await context.bot.send_message(chat_id=user["user_id"], text=message)
            success_count += 1
            logger.info(f"Sent broadcast to user {user['user_id']}")
        except Exception as e:
            logger.error(f"Failed to send broadcast to user {user['user_id']}: {e}")
            fail_count += 1

    await update.message.reply_text(
        f"Broadcast completed:\n"
        f"Sent to {success_count} users\n"
        f"Failed for {fail_count} users"
    )
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"Admin {user_id} broadcasted message:\n{message}\n"
             f"Sent to {success_count} users, failed for {fail_count} users."
    )
    logger.info(f"Broadcast by user {user_id}: sent to {success_count}, failed for {fail_count}")

async def pbroadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Pbroadcast command by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized pbroadcast attempt by user {user_id}")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        logger.info(f"No pbroadcast message provided by user {user_id}")
        await update.message.reply_text("Please provide a message to pbroadcast. Usage: /pbroadcast <message>")
        return

    message = " ".join(context.args)
    users = await db.get_all_users()
    success_count = 0
    fail_count = 0

    for user in users:
        try:
            msg = await context.bot.send_message(chat_id=user["user_id"], text=message)
            await context.bot.pin_chat_message(
                chat_id=user["user_id"],
                message_id=msg.message_id,
                disable_notification=True
            )
            success_count += 1
            logger.info(f"Sent and pinned pbroadcast to user {user['user_id']}")
        except Exception as e:
            logger.error(f"Failed to send/pin pbroadcast to user {user['user_id']}: {e}")
            fail_count += 1

    await update.message.reply_text(
        f"Pinned broadcast completed:\n"
        f"Sent and pinned to {success_count} users\n"
        f"Failed for {fail_count} users"
    )
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"Admin {user_id} pbroadcasted message:\n{message}\n"
             f"Sent and pinned to {success_count} users, failed for {fail_count} users."
    )
    logger.info(f"Pbroadcast by user {user_id}: sent to {success_count}, failed for {fail_count}")

def register_handlers(application: Application):
    logger.info("Registering broadcast and pbroadcast handlers")
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("pbroadcast", pbroadcast))