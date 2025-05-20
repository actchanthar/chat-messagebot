import os
from telegram.ext import Application
from config import BOT_TOKEN
from database.database import init_db
from plugins import (
    start, withdrawal, balance, top, help, message_handler, broadcast, users,
    addgroup, checkgroup, setphonebill, couple, transfer, referral, admin
)
import logging

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

def main():
    try:
        logger.debug("Starting bot initialization")

        # Use environment variables with fallback to config.py
        bot_token = os.getenv('BOT_TOKEN', BOT_TOKEN)
        logger.info("Checking environment variables")
        required_vars = ['BOT_TOKEN', 'MONGODB_URL', 'MONGODB_NAME']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.warning(f"Missing environment variables: {', '.join(missing_vars)}. Falling back to config.py values.")

        # Build the Telegram application
        logger.info("Building Telegram application")
        application = Application.builder().token(bot_token).build()
        logger.info("Telegram application built successfully")

        # Initialize the database
        logger.info("Initializing database with bot client")
        init_db(application.bot)
        logger.info("Database initialized successfully")

        # Verify database initialization
        from database.database import db
        if db is None:
            logger.error("Database initialization failed: db is None")
            raise RuntimeError("Database initialization failed")

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
        logger.info("All plugin handlers registered successfully")

        # Start polling
        logger.info("Starting bot polling")
        application.run_polling()
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()