import logging
from telegram.ext import Application
from config import BOT_TOKEN
from plugins import (
    start,
    withdrawal,
    message_handler,  # Must reference message_handler
    top,
    addgroup,
    checkgroup,
    setphonebill,
    users,
    broadcast,
    help,
    channels,
    add_bonus,
    restwithdraw,
    transfer,
    couple,
    balance
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting bot...")
    application = Application.builder().token(BOT_TOKEN).build()

    start.register_handlers(application)
    withdrawal.register_handlers(application)
    message_handler.register_handlers(application)
    top.register_handlers(application)
    addgroup.register_handlers(application)
    checkgroup.register_handlers(application)
    setphonebill.register_handlers(application)
    users.register_handlers(application)
    broadcast.register_handlers(application)
    help.register_handlers(application)
    channels.register_handlers(application)
    add_bonus.register_handlers(application)
    restwithdraw.register_handlers(application)
    transfer.register_handlers(application)
    couple.register_handlers(application)
    balance.register_handlers(application)

    logger.info("Bot started. Polling...")
    application.run_polling(allowed_updates=["message", "callback_query", "chat_member"])

if __name__ == "__main__":
    main()