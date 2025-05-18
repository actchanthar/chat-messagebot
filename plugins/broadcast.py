from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import ADMIN_IDS, GROUP_CHAT_IDS, LOG_CHANNEL_ID
import logging
from telegram.error import Forbidden, TelegramError

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

from database.database import db

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        logger.info(f"Non-admin {user_id} attempted /broadcast")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Please provide a message to broadcast. Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    users = await db.get_all_users()
    sent_count = 0
    failed_count = 0

    for user in users:
        user_id = user["user_id"]
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            sent_count += 1
            logger.info(f"Broadcast sent to user {user_id}")
        except (Forbidden, TelegramError) as e:
            logger.error(f"Broadcast failed for user {user_id}: {e}")
            await db.mark_broadcast_failure(user_id)
            failed_count += 1

    for group_id in GROUP_CHAT_IDS:
        try:
            bot_id = (await context.bot.get_me()).id
            await context.bot.get_chat_member(chat_id=group_id, user_id=bot_id)
            await context.bot.send_message(chat_id=group_id, text=message)
            logger.info(f"Broadcast sent to group {group_id}")
        except Forbidden as e:
            logger.error(f"Broadcast failed for group {group_id}: {e}")
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Warning: Bot is not a member of group {group_id}. Please add @{(await context.bot.get_me()).username} as an admin."
            )
        except TelegramError as e:
            logger.error(f"Broadcast failed for group {group_id}: {e}")

    summary = f"Broadcast completed: Sent to {sent_count} users, failed for {failed_count} users."
    await update.message.reply_text(summary)
    await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=summary)
    logger.info(summary)

def register_handlers(application: Application):
    logger.info("Registering broadcast handlers")
    application.add_handler(CommandHandler("broadcast", broadcast))