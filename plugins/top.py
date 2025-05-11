from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import config
import logging

logger = logging.getLogger(__name__)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Received /top command from user {user_id} in chat {chat_id}")

    try:
        top_users = await db.get_top_users()
        top_text = "ထိပ်တန်းအသုံးပြုသူ ၁၀ ဦး:\n"
        if not top_users:
            top_text += "အဆင့်သတ်မှတ်ချက်မရှိသေးပါ။\n"
        else:
            for i, user in enumerate(top_users, 1):
                top_text += f"{i}. {user['name']}: {user['messages']} စာတို၊ {user['balance']} {config.CURRENCY}\n"

        await update.message.reply_text(top_text)
        logger.info(f"Sent /top response to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to process /top for user {user_id} in chat {chat_id}: {e}")
        raise

def register_handlers(application):
    logger.info("Registering top handler")
    application.add_handler(CommandHandler("top", top))