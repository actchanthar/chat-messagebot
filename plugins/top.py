from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import ADMIN_IDS, LOG_CHANNEL_ID
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"/top command initiated by user {user_id} in chat {chat_id}")

    top_users = db.get_top_users_by_invites()
    phone_bill_reward = db.get_phone_bill_reward_text()
    total_users = db.get_total_users()

    message = (
        f"🏆 Top Users by Invites (Phone Bill Reward: {phone_bill_reward}):\n\n"
        f"Total Users: {total_users}\n\n"
    )
    for i, user in enumerate(top_users, 1):
        message += (
            f"{i}. <b>{user['name']}</b> - {user.get('invited_users', 0)} invites, "
            f"{user.get('balance', 0)} kyat\n"
        )

    try:
        await update.message.reply_text(message, parse_mode="HTML")
        logger.info(f"Sent top users list to user {user_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send /top reply to user {user_id}: {e}")
        try:
            # Fallback: Send as new message
            await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
            logger.info(f"Sent top users list as new message to user {user_id} in chat {chat_id}")
        except Exception as send_error:
            logger.error(f"Failed to send /top as new message to user {user_id}: {send_error}")
        try:
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Failed to send /top response to {user_id}: {e}"
            )
        except Exception as log_error:
            logger.error(f"Failed to log /top error to {LOG_CHANNEL_ID}: {log_error}")

def register_handlers(application: Application):
    logger.info("Registering top handlers")
    application.add_handler(CommandHandler("top", top))