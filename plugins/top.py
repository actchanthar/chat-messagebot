from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Top command initiated by user {user_id} in chat {chat_id}")

    top_users = await db.get_top_users()
    if not top_users:
        await update.message.reply_text("No top users available yet.")
        logger.warning(f"No top users found for user {user_id}")
        return

    top_message = "🏆 Top Users:\n"
    for i, user in enumerate(top_users, 1):
        messages = user.get("messages", 0)
        balance = user.get("balance", 0)
        top_message += f"{i}. {user['name']}: {messages} စာတို၊ {balance} {CURRENCY}\n"

    await update.message.reply_text(top_message)
    logger.info(f"Sent top users list to user {user_id} in chat {chat_id}")

def register_handlers(application: Application):
    logger.info("Registering top handlers")
    application.add_handler(CommandHandler("top", top))