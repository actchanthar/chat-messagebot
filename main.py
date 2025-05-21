import asyncio
import logging
from telegram.ext import Application
from config import BOT_TOKEN
from plugins import (
    start, withdrawal, balance, top, help, message_handler, broadcast, users,
    addgroup, checkgroup, setphonebill, referral_users, couple, channel_management,
    check_subscription, setinvite, add_bonus, setmessage, restwithdraw, transfer,
    toggle_counting, pbroadcast
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    try:
        # Initialize the application
        application = Application.builder().token(BOT_TOKEN).build()

        # Register all handlers
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
        referral_users.register_handlers(application)
        couple.register_handlers(application)
        channel_management.register_handlers(application)
        check_subscription.register_handlers(application)
        setinvite.register_handlers(application)
        add_bonus.register_handlers(application)
        setmessage.register_handlers(application)
        restwithdraw.register_handlers(application)
        transfer.register_handlers(application)
        toggle_counting.register_handlers(application)
        pbroadcast.register_handlers(application)

        # Start polling
        logger.info("Starting bot polling...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            drop_pending_updates=True,  # Ignore updates received while bot was offline
            allowed_updates=["message", "callback_query", "chat_member"]
        )

        # Keep the bot running until stopped
        logger.info("Bot is running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(3600)  # Sleep to keep the event loop alive

    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        logger.info("Shutting down bot...")
        if 'application' in locals():
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
        logger.info("Bot shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())