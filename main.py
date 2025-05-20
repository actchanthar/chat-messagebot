import logging
import logging.handlers
import sys
import os
from telegram.ext import Application
from database.database import init_db
from plugins import start, balance, message_handler

# Set up logging
log_file = '/tmp/bot.log'
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    ]
)
logger = logging.getLogger(__name__)
logger.debug("Logging initialized in main.py")

try:
    BOT_TOKEN = os.getenv('BOT_TOKEN', '7784918819:AAHS_tdSRck51UlgW_RQZ1LMSsXrLzqD7Oo')
    logger.debug(f"Using BOT_TOKEN (partial): {BOT_TOKEN[:10]}...")

    def main():
        try:
            logger.debug("Starting bot initialization")
            logger.debug(f"Python version: {sys.version}")
            logger.debug(f"Working directory: {os.getcwd()}")
            logger.debug(f"Files in directory: {os.listdir('.')}")

            # Build Telegram application
            logger.info("Building Telegram application")
            application = Application.builder().token(BOT_TOKEN).build()
            logger.info("Telegram application built successfully")

            # Initialize database
            logger.info("Initializing database")
            init_db(application.bot)
            logger.info("Database initialized successfully")

            # Verify database
            from database.database import db
            if db is None:
                logger.error("Database initialization failed: db is None")
                raise RuntimeError("Database initialization failed")

            # Register handlers
            logger.info("Registering plugin handlers")
            start.register_handlers(application)
            balance.register_handlers(application)
            message_handler.register_handlers(application)
            logger.info("Handlers registered successfully")

            # Start polling
            logger.info("Starting bot polling")
            application.run_polling()
        except Exception as e:
            logger.error(f"Fatal error in main: {e}", exc_info=True)
            raise

    if __name__ == "__main__":
        logger.debug("Entering main script")
        main()

except Exception as e:
    logger.error(f"Critical error before main: {e}", exc_info=True)
    raise