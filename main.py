from telegram.ext import Application
from config import BOT_TOKEN
from plugins import (
    start, withdrawal, balance, top, help, message_handler, broadcast, users,
    addgroup, checkgroup, setphonebill, subscription, couple, transfer,
    setinvite, setmessage, addchnl, callbacks
)

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    start.register_handlers(application)
    withdrawal.register_handlers(application)
    balance.register_handlers(application)
    top.register_handlers(application)
    help.register_handlers(application)
    message_handler.register_handlers(application)
    broadcast.register_handlers(application)
    users.register_handlers(application)
    addgroup.register_handlers(application)
    checkgroup.register_handlers(application)
    setphonebill.register_handlers(application)
    subscription.register_handlers(application)
    couple.register_handlers(application)
    transfer.register_handlers(application)
    setinvite.register_handlers(application)
    setmessage.register_handlers(application)
    addchnl.register_handlers(application)
    callbacks.register_handlers(application)
    try:
        application.run_polling(allowed_updates=["message", "callback_query"])
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()