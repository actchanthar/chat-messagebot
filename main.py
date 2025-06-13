import logging
import traceback
from telegram import Update, BotCommand
from telegram.ext import Application, ContextTypes
from config import BOT_TOKEN
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
    rmamount,
    setamount  # New plugin for referral reward
)

# Configure logging with file handler
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def post_init(application: Application) -> None:
    logger.info("Bot is starting...")
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("balance", "Check your balance"),
        BotCommand("top", "View top users"),
        BotCommand("withdraw", "Withdraw earnings"),
        BotCommand("couple", "Find a random couple match"),
        BotCommand("transfer", "Transfer balance to another user"),
        BotCommand("help", "Show help message"),
        BotCommand("rmamount", "Reset daily withdrawal amount (admin only)"),
        BotCommand("addgroup", "Add a group for message counting (admin only)"),
        BotCommand("add_bonus", "Add bonus to a user (admin only)"),
        BotCommand("setinvite", "Set invite count for a user (admin only)"),
        BotCommand("setmessage", "Set message count for a user (admin only)"),
        BotCommand("setamount", "Set referral reward amount (admin only)")
    ]
    try:
        await application.bot.set_my_commandscommands)
        logger.info("Bot commands set successfully")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    error_message = f"Update {update} caused error: {context.error}\n{traceback.format_exc()}"
    logger.error(error_message)
    if update and (update.message or update.callback_query):
        try:
            await (update.message or update.callback_query.message).reply_text(
                "An error occurred. Please try again later or contact support."
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

async def post_shutdown(application: Application) -> None:
    logger.info("Bot is shutting down...")

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()

    application.add_error_handler(error_handler)

    logger.info("Registering plugin handlers")
    addgroup.register_handlers(application)
    admin.register_handlers(application)
    balance.register_handlers(application)
    broadcast.register_handlers(application)
    channel.register_handlers(application)
    checkgroup.register_handlers(application)
    couple.register_handlers(application)
    help.register_handlers(application)
    setphonebill.register_handlers(application)
    start.register_handlers(application)
    top.register_handlers(application)
    transfer.register_handlers(application)
    users.register_handlers(application)
    withdrawal.register_handlers(application)
    rmamount.register_handlers(application)
    setamount.register_handlers(application)  # Register new plugin
    message_handler.register_handlers(application)

    logger.info("Starting bot")
    try:
        application.run_polling(allowed_updates=["message", "callback_query"])
    except Exception as e:
        logger.error(f"Bot crashed: {e}\n{traceback.format_exc()}")
    finally:
        logger.info("Bot stopped")

if __name__ == "__main__":
    main()