import os
import logging
import asyncio
from telegram.ext import Application

# Import configuration
import config

# Import database
from database import db

# Import plugins
from plugins import start, balance, stats, admin, message_handler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """Start the bot."""
    # Check for bot token
    if not config.BOT_TOKEN:
        logger.error("TELEGRAM_TOKEN environment variable not set")
        return
    
    # Connect to database
    if not await db.connect():
        logger.error("Failed to connect to database")
        return
    
    # Create the Application
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Register handlers from plugins
    start.register_handlers(application)
    balance.register_handlers(application)
    stats.register_handlers(application)
    admin.register_handlers(application)
    message_handler.register_handlers(application)
    
    logger.info("Starting bot")
    
    # Start the Bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    try:
        # Run the bot until the user presses Ctrl-C
        await application.updater.start_polling()
        await asyncio.Event().wait()  # Wait forever
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopping...")
    finally:
        # Close database connection
        await db.close()
        # Stop the Bot
        await application.stop()
        await application.updater.stop()
        await application.shutdown()

if __name__ == '__main__':
    asyncio.run(main())