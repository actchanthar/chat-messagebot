from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Broadcast command initiated by user {user_id} in chat {chat_id}")

    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Please provide a message to broadcast. Usage: /broadcast <message>")
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
            await context.bot.send_message(user["user_id"], message, parse_mode="HTML")
            success_count += 1
        except Exception as e:
            failure_count += 1
            logger.error(f"Failed to broadcast to user {user['user_id']}: {e}")

    result_message = f"Broadcast completed: Sent to {success_count} users, failed for {failure_count} users."
    await update.message.reply_text(result_message)
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"Broadcast by {update.effective_user.full_name}: {message}\n{result_message}"
    )

async def pbroadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Pbroadcast command initiated by user {user_id} in chat {chat_id}")

    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Please provide a message to broadcast. Usage: /pbroadcast <message>")
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
            msg = await context.bot.send_message(user["user_id"], message, parse_mode="HTML")
            await context.bot.pin_chat_message(user["user_id"], msg.message_id, disable_notification=True)
            success_count += 1
        except Exception as e:
            failure_count += 1
            logger.error(f"Failed to broadcast to user {user['user_id']}: {e}")

    result_message = f"Pinned broadcast completed: Sent to {success_count} users, failed for {failure_count} users."
    await update.message.reply_text(result_message)
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"Pinned broadcast by {update.effective_user.full_name}: {message}\n{result_message}"
    )

def register_handlers(application: Application):
    logger.info("Registering broadcast handlers")
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("pbroadcast", pbroadcast))