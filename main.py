import logging
from telegram.ext import Application
from config import BOT_TOKEN

# Import plugin handlers
from plugins import (
    addgroup,
    balance,
    broadcast,
    checkgroup,
    couple,
    help,
    message_handler,
    setphonebill,
    start,
    top,
    transfer,
    users,
    withdrawal
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def post_init(application: Application) -> None:
    logger.info("Bot is starting...")
    await application.bot.set_my_commands([
        ("start", "Start the bot"),
        ("balance", "Check your balance"),
        ("top", "View top users"),
        ("withdraw", "Withdraw earnings"),
        ("couple", "Find a random couple match"),
        ("transfer", "Transfer balance to another user"),
        ("help", "Show help message")
    ])
    logger.info("Bot commands set successfully")

def main() -> None:
    # Initialize the application
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Register plugin handlers
    logger.info("Registering plugin handlers")
    addgroup.register_handlers(application)
    balance.register_handlers(application)
    broadcast.register_handlers(application)
    checkgroup.register_handlers(application)
    couple.register_handlers(application)
    help.register_handlers(application)
    message_handler.register_handlers(application)
    setphonebill.register_handlers(application)
    start.register_handlers(application)
    top.register_handlers(application)
    transfer.register_handlers(application)
    users.register_handlers(application)
    withdrawal.register_handlers(application)

    # Start the bot
    logger.info("Starting bot")
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()