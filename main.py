import logging
import traceback
from telegram import Update
from telegram.ext import Application, ContextTypes

from config import BOT_TOKEN

# Import plugin handlers (these should now resolve to modules)
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
    rmamount
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
        ("rmamount", "Reset daily withdrawal amount (admin only)"),
        ("addgroup", "Add a group for message counting (admin only)"),
        ("Add_bonus", "Add bonus to a user (admin only)"),
        ("setinvite", "Set invite count for a user (admin only)"),
        ("setmessage", "Set message count for a user (admin only)")
    ])
    logger.info("Bot commands set successfully")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    error_message = f"Update {update} caused error: {context.error}\n{traceback.format_exc()}"
    logger.error(error_message)
    if update and update.message:
        await update.message.reply_text("An error occurred. Please try again later or contact support.")

async def post_shutdown(application: Application) -> None:
    logger.info("Bot is shutting down...")

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()

    application.add_error_handler(error_handler)

    logger.info("Registering plugin handlers")
    
    # Group 0: General command handlers
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
    
    # Group 1: Conversation and admin-specific command handlers
    withdrawal.register_handlers(application)  # Group 1
    rmamount.register_handlers(application)    # Group 1

    # Group 2: Message handler
    message_handler.register_handlers(application)  # Group 2

    logger.info("Starting bot")
    try:
        application.run_polling(allowed_updates=["message", "callback_query"])
    except Exception as e:
        logger.error(f"Bot crashed: {e}\n{traceback.format_exc()}")
    finally:
        logger.info("Bot stopped")

if __name__ == "__main__":
    main()