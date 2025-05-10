import asyncio
import logging
from telegram.ext import Application
import config
from database.database import Database
from plugins import start, balance, stats, admin, message_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

async def main():
    if not config.BOT_TOKEN:
        logger.error("TELEGRAM_TOKEN not set")
        return
    
    await db.init()
    application = Application.builder().token(config.BOT_TOKEN).build()

    start.register_handlers(application)
    balance.register_handlers(application)
    stats.register_handlers(application)
    admin.register_handlers(application)
    message_handler.register_handlers(application)

    logger.info("Starting bot")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
