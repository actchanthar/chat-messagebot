from telegram.ext import Application
from config import BOT_TOKEN
from plugins import (
    start, withdrawal, balance, top, help, message_handler, broadcast, users,
    addgroup, checkgroup, setphonebill, referral_users, couple, channel_management,
    check_subscription, setinvite, add_bonus, setmessage, restwithdraw, transfer,
    toggle_counting, pbroadcast
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
    referral_users.register_handlers(application)
    couple.register_handlers(application)
    channel_management.register_handlers(application)
    check_subscription.register_handlers(application)
    setinvite.register_handlers(application)
    add_bonus.register_handlers(application)
    setmessage.register_handlers(application)
    restwithdraw.register_handlers(application)
    transfer.register_handlers(application)
    toggle_counting.register_handlers(application)
    pbroadcast.register_handlers(application)
    application.run_polling()

if __name__ == "__main__":
    main()