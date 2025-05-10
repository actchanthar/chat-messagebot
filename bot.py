import asyncio
import logging
from telegram.ext import Application
import config
from database.database import db
from plugins import start, balance, stats, admin, message_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    if not config.BOT_TOKEN:
        logger.error("TELEGRAM_TOKEN not set")
        return
    
    # Initialize database
    await db.init()

    # Create and configure the Application
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Register handlers
    start.register_handlers(application)
    balance.register_handlers(application)
    stats.register_handlers(application)
    admin.register_handlers(application)
    message_handler.register_handlers(application)

    logger.info("Starting bot")

    try:
        # Initialize and start polling
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # Keep the bot running until interrupted
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Bot stopping...")
    finally:
        # Properly shut down
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())