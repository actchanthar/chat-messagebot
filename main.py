from telegram.ext import Application
from config import BOT_TOKEN
from plugins.start import register_handlers as start_handlers
from plugins.withdrawal import register_handlers as withdrawal_handlers
from plugins.balance import register_handlers as balance_handlers
from plugins.top import register_handlers as top_handlers
from plugins.help import register_handlers as help_handlers
from plugins.message_handler import register_handlers as message_handlers
from plugins.broadcast import register_handlers as broadcast_handlers
from plugins.users import register_handlers as users_handlers
from plugins.addgroup import register_handlers as addgroup_handlers
from plugins.checkgroup import register_handlers as checkgroup_handlers
from plugins.setphonebill import register_handlers as setphonebill_handlers
from plugins.checksubscription import register_handlers as checksubscription_handlers
from plugins.couple import register_handlers as couple_handlers
from plugins.referral_users import register_handlers as referral_users_handlers
from plugins.admin import register_handlers as admin_handlers

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Register handlers from plugins
    start_handlers(application)
    withdrawal_handlers(application)
    balance_handlers(application)
    top_handlers(application)
    help_handlers(application)
    message_handlers(application)
    broadcast_handlers(application)
    users_handlers(application)
    addgroup_handlers(application)
    checkgroup_handlers(application)
    setphonebill_handlers(application)
    checksubscription_handlers(application)
    couple_handlers(application)
    referral_users_handlers(application)
    admin_handlers(application)

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()