import logging
import traceback
from telegram import Update
from telegram.ext import Application, ContextTypes

from config import BOT_TOKEN

# Import plugin handlers
from plugins import (
    addgroup,
    admin,
    balance,
    broadcast,
    channel,
    checkgroup,
    couple,
    help,
    message_handler,
    setphonebill,
    start,
    top,
    transfer,
    users,
    withdrawal,
    rmamount  # Added rmamount plugin
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
        ("help", "Show help message"),
        ("rmamount", "Reset daily withdrawal amount (admin only)"),  # Added rmamount command
        ("addgroup", "Add a group for message counting (admin only)"),  # Added from addgroup.py
        ("Add_bonus", "Add bonus to a user (admin only)"),  # Added from admin.py
        ("setinvite", "Set invite count for a user (admin only)"),  # Added from admin.py
        ("setmessage", "Set message count for a user (admin only)")   # Added from admin.py
    ])
    logger.info("Bot commands set successfully")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Log the error with a stack trace for better debugging
    error_message = f"Update {update} caused error: {context.error}\n{traceback.format_exc()}"
    logger.error(error_message)
    # Notify the user of the error
    if update and update.message:
        await update.message.reply_text("An error occurred. Please try again later or contact support.")

async def post_shutdown(application: Application) -> None:
    logger.info("Bot is shutting down...")

def main() -> None:
    # Initialize the application with post_shutdown hook
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()

    # Register error handler
    application.add_error_handler(error_handler)

    # Register plugin handlers with specific groups to avoid conflicts
    logger.info("Registering plugin handlers")
    
    # Group 0: General command handlers (default group)
    addgroup.register_handlers(application)    # Group 0
    admin.register_handlers(application)       # Group 0
    balance.register_handlers(application)     # Group 0
    broadcast.register_handlers(application)   # Group 0
    channel.register_handlers(application)     # Group 0
    checkgroup.register_handlers(application)  # Group 0
    couple.register_handlers(application)      # Group 0
    help.register_handlers(application)        # Group 0
    setphonebill.register_handlers(application)# Group 0
    start.register_handlers(application)       # Group 0
    top.register_handlers(application)         # Group 0
    transfer.register_handlers(application)    # Group 0
    users.register_handlers(application)       # Group 0
    
    # Group 1: Conversation and admin-specific command handlers (higher priority)
    withdrawal.register_handlers(application)  # Group 1 (conversation handler)
    rmamount.register_handlers(application)    # Group 1 (admin command)

    # Group 2: Message handler (lowest priority to avoid intercepting conversation messages)
    message_handler.register_handlers(application)  # Group 2

    # Start the bot
    logger.info("Starting bot")
    try:
        application.run_polling(allowed_updates=["message", "callback_query"])
    except Exception as e:
        logger.error(f"Bot crashed: {e}\n{traceback.format_exc()}")
    finally:
        logger.info("Bot stopped")

if __name__ == "__main__":
    main()