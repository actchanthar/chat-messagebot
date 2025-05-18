from telegram.ext import Application
from telegram import Update
from config import BOT_TOKEN, LOG_CHANNEL_ID
from plugins.start import register_handlers as start_handlers
from plugins.withdrawal import register_handlers as withdrawal_handlers
from plugins.add_bonus import register_handlers as add_bonus_handlers
from plugins.message_handler import register_handlers as message_handler_handlers
from plugins.addgroup import register_handlers as addgroup_handlers
from plugins.broadcast import register_handlers as broadcast_handlers
from plugins.channel_management import register_handlers as channel_management_handlers
from plugins.checkgroup import register_handlers as checkgroup_handlers
from plugins.help import register_handlers as help_handlers
from plugins.setinvite import register_handlers as setinvite_handlers
from plugins.setphonebill import register_handlers as setphonebill_handlers
from plugins.top import register_handlers as top_handlers
from plugins.users import register_handlers as users_handlers
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def error_handler(update: Update, context):
    logger.error(f"Update {update} caused error {context.error}")
    try:
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Error: {context.error}"
        )
    except Exception as e:
        logger.error(f"Failed to send error to log channel {LOG_CHANNEL_ID}: {e}")

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Register handlers
    start_handlers(application)
    withdrawal_handlers(application)
    add_bonus_handlers(application)
    message_handler_handlers(application)
    addgroup_handlers(application)
    broadcast_handlers(application)
    channel_management_handlers(application)
    checkgroup_handlers(application)
    help_handlers(application)
    setinvite_handlers(application)
    setphonebill_handlers(application)
    top_handlers(application)
    users_handlers(application)

    # Add error handler
    application.add_error_handler(error_handler)

    # Start polling
    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()