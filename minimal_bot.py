import logging
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "your_bot_token"  # REPLACE
GROUP_CHAT_ID = "-1002061898677"
message_counts = {}

async def count_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)
    if chat_id != GROUP_CHAT_ID:
        logger.debug(f"Ignoring chat {chat_id}")
        return
    message_counts[user_id] = message_counts.get(user_id, 0) + 1
    logger.info(f"User {user_id}: {message_counts[user_id]} messages")
    await update.message.reply_text(f"Messages: {message_counts[user_id]}")

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text(f"Chat ID: {chat_id}")

async def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, count_message))
    application.add_handler(CommandHandler("getchatid", get_chat_id))
    logger.info("Starting minimal bot")
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())