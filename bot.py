import logging
from telegram.ext import Application
import config
from plugins.message_handler import register_handlers
from plugins.balance import register_handlers as register_balance_handlers
from plugins.admin import register_handlers as register_admin_handlers

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting bot")
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Register all handlers
    register_handlers(application)
    register_balance_handlers(application)
    register_admin_handlers(application)

    # Start the bot
    logger.info("Bot is running")
    application.run_polling()

if __name__ == '__main__':
    main()