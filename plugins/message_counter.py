from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from config import GROUP_CHAT_IDS
from database.database import db
import logging

logger = logging.getLogger(__name__)

async def count_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    if chat_id not in GROUP_CHAT_IDS:
        return
    user = db.get_user(user_id)
    if not user:
        return
    group_messages = user.get("group_messages", 0) + 1
    db.update_user(user_id, {"group_messages": group_messages})

def register_handlers(application: Application):
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Chat(chat_id=GROUP_CHAT_IDS), count_message))