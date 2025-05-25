import logging
import asyncio
from telegram.ext import Application
from telegram import Bot
from config import BOT_TOKEN, ADMIN_IDS
from database.database import db
from plugins import (
    start,
    withdrawal,
    message_handler,
    setmessage,
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

async def validate_bot_token(token: str) -> bool:
    try:
        bot = Bot(token)
        bot_info = await bot.get_me()
        logger.info(f"Bot token validated successfully: @{bot_info.username}")
        return True
    except Exception as e:
        logger.error(f"Invalid bot token: {str(e)}")
        return False

async def post_init(application: Application) -> None:
    try:
        application.bot_data["admin_ids"] = ADMIN_IDS
        await db.migrate_users()
        logger.info("Post-init completed: admin IDs set, user migration done")
    except Exception as e:
        logger.error(f"Post-init failed: {str(e)}")
        raise

async def main():
    logger.info("Starting bot...")
    
    # Validate bot token
    if not await validate_bot_token(BOT_TOKEN):
        logger.error("Bot cannot start due to invalid token")
        return

    try:
        # Build application
        application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
        logger.info("Application built successfully")
    except Exception as e:
        logger.error(f"Failed to build application: {str(e)}")
        return

    try:
        # Register handlers
        start.register_handlers(application)
        withdrawal.register_handlers(application)
        message_handler.register_handlers(application)
        setmessage.register_handlers(application)
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
        logger.info("All handlers registered")
    except Exception as e:
        logger.error(f"Failed to register handlers: {str(e)}")
        return

    try:
        logger.info("Initializing application...")
        await application.initialize()
        logger.info("Application initialized. Starting polling...")
        await application.run_polling(
            allowed_updates=["message", "callback_query", "chat_member"],
            drop_pending_updates=True
        )
        logger.info("Polling stopped. Shutting down application...")
        await application.shutdown()
        logger.info("Application shut down successfully")
    except Exception as e:
        logger.error(f"Application failed: {str(e)}")
        raise
    finally:
        logger.info("Ensuring application shutdown...")
        await application.shutdown()

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except Exception as e:
        logger.error(f"Main loop failed: {str(e)}")