from telegram.ext import Application
from config import BOT_TOKEN
from plugins import (
    start, withdrawal, balance, top, help, message_handler, broadcast, users,
    addgroup, checkgroup, setphonebill, checksubscription, couple, referral_users, admin
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
    checksubscription.register_handlers(application)
    couple.register_handlers(application)
    referral_users.register_handlers(application)
    admin.register_handlers(application)
    application.run_polling()

if __name__ == "__main__":
    main()