# main.py
import logging
from telegram.ext import Application
from config import BOT_TOKEN
from plugins.start import register_handlers as start_handlers
from plugins.check_subscription import register_handlers as check_subscription_handlers
from plugins.channel_management import register_handlers as channel_management_handlers
from plugins.withdrawal import register_handlers as withdrawal_handlers

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    start_handlers(application)
    check_subscription_handlers(application)
    channel_management_handlers(application)
    withdrawal_handlers(application)
    
    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()