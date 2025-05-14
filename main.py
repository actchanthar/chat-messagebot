# main.py
from telegram.ext import Application
from plugins import start, withdrawal, balance, top, help, message_handler, broadcast, users  # Add users
from config import BOT_TOKEN as TOKEN

def main():
    application = Application.builder().token(TOKEN).build()
    start.register_handlers(application)
    withdrawal.register_handlers(application)
    balance.register_handlers(application)
    top.register_handlers(application)
    help.register_handlers(application)
    message_handler.register_handlers(application)
    broadcast.register_handlers(application)
    users.register_handlers(application)  # Register the users plugin
    application.run_polling()

if __name__ == "__main__":
    main()