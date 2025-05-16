# main.py
import logging
from telegram.ext import Application
from config import BOT_TOKEN
from plugins.start import register_handlers as start_handlers
from plugins.withdrawal import register_handlers as withdrawal_handlers
from plugins.add_bonus import register_handlers as add_bonus_handlers  # Keep this line

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    start_handlers(application)
    withdrawal_handlers(application)
    add_bonus_handlers(application)  # Keep this line

    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()