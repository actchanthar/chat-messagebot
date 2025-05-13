# main.py
from telegram.ext import Application
from plugins import start, withdrawal, balance, top, help, message_handler
from config import BOT_TOKEN

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Register handlers
    start.register_handlers(application)
    withdrawal.register_handlers(application)
    balance.register_handlers(application)
    top.register_handlers(application)
    help.register_handlers(application)
    message_handler.register_handlers(application)

    # Start the bot
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()