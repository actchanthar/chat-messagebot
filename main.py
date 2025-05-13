# main.py
from telegram.ext import Application
from plugins import start, withdrawal, balance, top, help, message_handler

def main():
    # Replace with your bot token
    application = Application.builder().token("7784918819:AAHS_tdSRck51UlgW_RQZ1LMSsXrLzqD7Oo").build()

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