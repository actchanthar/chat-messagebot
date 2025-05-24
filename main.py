from telegram.ext import Application
from telegram.request import HTTPXRequest
from telegram.error import Conflict
from config import BOT_TOKEN
from plugins.start import register_handlers as start_handlers
from plugins.withdrawal import register_handlers as withdrawal_handlers
from plugins.balance import register_handlers as balance_handlers
from plugins.top import register_handlers as top_handlers
from plugins.help import register_handlers as help_handlers
from plugins.message_handler import register_handlers as message_handlers
from plugins.broadcast import register_handlers as broadcast_handlers
from plugins.users import register_handlers as users_handlers
from plugins.addgroup import register_handlers as addgroup_handlers
from plugins.checkgroup import register_handlers as checkgroup_handlers
from plugins.setphonebill import register_handlers as setphonebill_handlers
from plugins.checksubscription import register_handlers as checksubscription_handlers
from plugins.couple import register_handlers as couple_handlers
from plugins.referral_users import register_handlers as referral_users_handlers
from plugins.admin import register_handlers as admin_handlers
from plugins.reset import register_handlers as reset_handlers
from plugins.on_off import register_handlers as on_off_handlers
from plugins.debug_count import register_handlers as debug_count_handlers
from plugins.test_count import register_handlers as test_count_handlers
from plugins.rmamount import register_handlers as rmamount_handlers
from plugins.check import register_handlers as check_handlers
from plugins.add_bonus import register_handlers as add_bonus_handlers
from plugins.grok import register_handlers as grok_handlers
from plugins.transfer import register_handlers as transfer_handlers
import logging
import asyncio

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Configure HTTPXRequest with timeouts and connection pool
    request = HTTPXRequest(
        connection_pool_size=20,
        read_timeout=30.0,
        write_timeout=30.0,
        connect_timeout=30.0,
        pool_timeout=30.0,
        http_version="1.1",
    )

    # Build the application
    application = Application.builder().token(BOT_TOKEN).request(request).build()

    # Error handler for conflicts
    async def error_handler(update, context):
        logger.error(f"Update {update} caused error {context.error}")
        if isinstance(context.error, Conflict):
            logger.warning("Detected getUpdates conflict. Attempting to recover...")
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    await context.application.updater.stop()
                    logger.info("Updater stopped due to conflict")
                    await asyncio.sleep(20)
                    await context.application.updater.start_polling(drop_pending_updates=True)
                    logger.info("Polling restarted successfully after conflict")
                    return
                except Exception as e:
                    logger.error(f"Retry {attempt + 1}/{max_retries} failed: {e}")
                    await asyncio.sleep(5)
            logger.error("Failed to recover from conflict after retries. Please check for duplicate bot instances.")
        else:
            logger.error(f"Unhandled error: {context.error}")

    application.add_error_handler(error_handler)

    # Register all handlers
    logger.info("Registering handlers...")
    start_handlers(application)
    withdrawal_handlers(application)
    balance_handlers(application)
    top_handlers(application)
    help_handlers(application)
    message_handlers(application)
    broadcast_handlers(application)
    users_handlers(application)
    addgroup_handlers(application)
    checkgroup_handlers(application)
    setphonebill_handlers(application)
    checksubscription_handlers(application)
    couple_handlers(application)
    referral_users_handlers(application)
    admin_handlers(application)
    reset_handlers(application)
    on_off_handlers(application)
    debug_count_handlers(application)
    test_count_handlers(application)
    rmamount_handlers(application)
    check_handlers(application)
    add_bonus_handlers(application)
    grok_handlers(application)
    transfer_handlers(application)

    # Pre-start cleanup to avoid conflicts
    logger.info("Performing pre-start cleanup...")
    try:
        # Run cleanup in a temporary event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Delete any existing webhook to ensure polling mode
            loop.run_until_complete(application.bot.delete_webhook(drop_pending_updates=True))
            logger.info("Deleted any existing webhook to ensure polling mode")
            loop.run_until_complete(asyncio.sleep(2))

            # Stop any previous polling sessions
            loop.run_until_complete(application.updater.stop())
            logger.info("Stopped any previous polling sessions")
            loop.run_until_complete(asyncio.sleep(5))
        finally:
            loop.close()
    except Exception as e:
        logger.warning(f"Error during pre-start cleanup: {e}")

    # Start the bot with polling
    logger.info("Starting bot with polling...")
    try:
        application.run_polling(
            drop_pending_updates=True,
            timeout=30,
            read_timeout=30.0,
            write_timeout=30.0,
            connect_timeout=30.0,
            pool_timeout=30.0,
        )
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    main()