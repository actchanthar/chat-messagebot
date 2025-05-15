from telegram.ext import Application
from plugins import start, withdrawal, balance, top, help, message_handler, broadcast, users

def main() -> None:
    application = Application.builder().token("7784918819:AAHS_tdSRck51UlgW_RQZ1LMSsXrLzqD7Oo").build()

    # Register all handlers
    start.register_handlers(application)
    withdrawal.register_handlers(application)
    balance.register_handlers(application)  # Ensure this line is present
    top.register_handlers(application)
    help.register_handlers(application)
    message_handler.register_handlers(application)
    broadcast.register_handlers(application)
    users.register_handlers(application)

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()