import logging
from telegram.ext import Application
from config import BOT_TOKEN
from plugins.start import register_handlers as start_handlers
from plugins.message_handler import register_handlers as message_handlers
from plugins.top import register_handlers as top_handlers
from plugins.broadcast import register_handlers as broadcast_handlers
from plugins.setphonebill import register_handlers as setphonebill_handlers
from plugins.withdrawal import register_handlers as withdrawal_handlers
from plugins.setinvite import register_handlers as setinvite_handlers
from plugins.check_subscription import register_handlers as checksubscription_handlers
from plugins.channel_management import register_handlers as channel_management_handlers  # Add this

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    # Register handlers
    start_handlers(application)
    message_handlers(application)
    top_handlers(application)
    broadcast_handlers(application)
    setphonebill_handlers(application)
    withdrawal_handlers(application)
    setinvite_handlers(application)
    checksubscription_handlers(application)
    channel_management_handlers(application)  # Add this

    logger.info("Starting bot")
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()