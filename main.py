import logging
from telegram.ext import Application, CommandHandler
from config import BOT_TOKEN
from plugins.start import register_handlers as start_handlers
from plugins.check_subscription import register_handlers as check_subscription_handlers
from plugins.channel_management import register_handlers as channel_management_handlers
from database.database import db  # Ensure db is imported for initialization

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    start_handlers(application)
    check_subscription_handlers(application)
    channel_management_handlers(application)
    
    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()