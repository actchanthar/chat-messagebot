from telegram.ext import Application
from config import BOT_TOKEN
from database.database import init_db
from plugins import (
    start, withdrawal, balance, top, help, message_handler, broadcast, users,
    addgroup, checkgroup, setphonebill, couple, transfer, referral, admin
)
import logging

# Configure logging to capture initialization errors
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Build the Telegram application
        logger.info("Building Telegram application")
        application = Application.builder().token(BOT_TOKEN).build()
        logger.info("Telegram application built successfully")

        # Initialize the database with the bot client
        logger.info("Initializing database")
        init_db(application.bot)
        logger.info("Database initialized successfully")

        # Register all plugin handlers
        logger.info("Registering plugin handlers")
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
        couple.register_handlers(application)
        transfer.register_handlers(application)
        referral.register_handlers(application)
        admin.register_handlers(application)
        logger.info("All plugin handlers registered")

        # Start polling
        logger.info("Starting bot polling")
        application.run_polling()
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise  # Re-raise to ensure Heroku logs the error and restarts if needed

if __name__ == "__main__":
    main()