import logging
import logging.handlers
import sys

# Set up logging before imports
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
    import os
    from telegram.ext import Application
    from config import BOT_TOKEN
    from database.database import init_db
    from plugins import start, balance, message_handler

    logger.debug("Imports completed successfully")

    def main():
        try:
            logger.debug("Starting bot initialization")
            logger.debug(f"Python version: {sys.version}")
            logger.debug(f"Telegram.ext version: {Application.__module__}")

            # Log environment variables
            logger.info("Checking environment variables")
            required_vars = ['BOT_TOKEN', 'MONGODB_URL', 'MONGODB_NAME']
            env_vars = {var: os.getenv(var) for var in required_vars}
            missing_vars = [var for var in required_vars if not env_vars[var]]
            if missing_vars:
                logger.warning(f"Missing environment variables: {', '.join(missing_vars)}. Using config.py values.")
            else:
                logger.info(f"Environment variables found: {', '.join(var for var in required_vars if env_vars[var])}")

            # Use environment variable with fallback to config.py
            bot_token = os.getenv('BOT_TOKEN', BOT_TOKEN)
            logger.debug(f"Using BOT_TOKEN (partial): {bot_token[:10]}...")

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

            # Register minimal plugin handlers
            logger.info("Registering plugin handlers")
            start.register_handlers(application)
            balance.register_handlers(application)
            message_handler.register_handlers(application)
            logger.info("Plugin handlers registered successfully")

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