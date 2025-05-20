from telegram import Update
from telegram.ext import Application, ContextTypes
from config import BOT_TOKEN
from plugins import (
    start, withdrawal, balance, top, help, message_handler, broadcast,
    users, addgroup, checkgroup, setphonebill, channel_management,
    misc, clone, on
)
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("An error occurred. Please try again later.")

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Register error handler
    application.add_error_handler(error_handler)

    # Register other handlers
    start.register_handlers(application)
    withdrawal.register_handlers(application)
    balance.register_handlers(application)
    top.register_handlers(application)
    help.register_handlers(application)
    message_handler.register_handlers(application)
    broadcast.register_handlers(application)
    users.register_handlers(application)
    addgroup.register_handlers(application)
    checkgroup.register_handlers(application)
    setphonebill.register_handlers(application)
    channel_management.register_handlers(application)
    misc.register_handlers(application)
    clone.register_handlers(application)
    on.register_handlers(application)

    application.run_polling()

if __name__ == "__main__":
    main()