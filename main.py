# main.py (or equivalent)
from plugins import start, withdrawal, balance, top, debug  # Add debug

def main():
    application = Application.builder().token("YOUR_BOT_TOKEN").build()

    # Register handlers
    start.register_handlers(application)
    withdrawal.register_handlers(application)
    balance.register_handlers(application)
    top.register_handlers(application)
    debug.register_handlers(application)  # Add this line

    application.run_polling()

if __name__ == "__main__":
    main()