import logging
import asyncio
from telegram.ext import Application
from telegram import Update
from config import BOT_TOKEN
from database import db
from plugins import start, withdrawal, balance, top, addgroup, checkgroup, setphonebill, broadcast

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize the application
application = Application.builder().token(BOT_TOKEN).build()

# Register handlers from plugins
start.register_handlers(application)
withdrawal.register_handlers(application)
balance.register_handlers(application)
top.register_handlers(application)
addgroup.register_handlers(application)
checkgroup.register_handlers(application)
setphonebill.register_handlers(application)
broadcast.register_handlers(application)

async def pre_start_cleanup():
    """Perform cleanup tasks before starting the bot."""
    logger.info("Performing pre-start cleanup...")
    try:
        # Delete any existing webhook to ensure polling mode
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Deleted any existing webhook to ensure polling mode")
    except Exception as e:
        logger.warning(f"Failed to delete webhook: {e}")

async def main():
    """Main function to run the bot."""
    # Run cleanup in the application’s event loop
    await pre_start_cleanup()

    # Start the bot with polling
    logger.info("Starting bot with polling...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")