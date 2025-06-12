import logging
import traceback
from telegram import Update, BotCommand
from telegram.ext import Application, ContextTypes
from config import BOT_TOKEN, LOG_CHANNEL_ID
from plugins import (
    admin,        # Handles /add_bonus, /setinvite, /setmessage
    addgroup,     # /addgroup
    balance,      # /balance
    broadcast,    # /broadcast, /pbroadcast
    channel,      # /addchnl, /delchnl, /listchnl
    checkgroup,   # /checkgroup
    couple,       # /couple
    help,         # /help
    message_handler,  # Group message counting
    setphonebill, # /setphonebill
    start,        # /start
    top,          # /top
    transfer,     # /transfer
    users,        # /users
    withdrawal,   # /withdraw
    rmamount,     # /rmamount
    restwithdraw  # /restwithdraw
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
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
        BotCommand("rmamount", "Deduct amount from user balance (admin only)"),
        BotCommand("addgroup", "Add a group for message counting (admin only)"),
        BotCommand("add_bonus", "Add bonus to a user (admin only)"),
        BotCommand("setinvite", "Set invite count for a user (admin only)"),
        BotCommand("setmessage", "Set messages per kyat (admin only)")
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands set successfully")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    error_message = f"Update {update} caused error: {context.error}\n{traceback.format_exc()}"
    logger.error(error_message)
    if update and update.effective_message:
        await update.effective_message.reply_text("An error occurred. Please try again or contact support.")
    try:
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"Bot Error:\n{error_message[:4000]}"
        )
    except Exception as e:
        logger.error(f"Failed to send error to log channel: {e}")

async def post_shutdown(application: Application) -> None:
    logger.info("Bot is shutting down...")

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()
    application.add_error_handler(error_handler)
    logger.info("Registering plugin handlers")
    
    admin.register_handlers(application)        # Group 0
    addgroup.register_handlers(application)     # Group 0
    balance.register_handlers(application)      # Group 0
    broadcast.register_handlers(application)    # Group 0
    channel.register_handlers(application)      # Group 0
    checkgroup.register_handlers(application)   # Group 0
    couple.register_handlers(application)       # Group 0
    help.register_handlers(application)         # Group 0
    setphonebill.register_handlers(application) # Group 0
    start.register_handlers(application)        # Group 0
    top.register_handlers(application)          # Group 0
    transfer.register_handlers(application)     # Group 0
    users.register_handlers(application)        # Group 0
    withdrawal.register_handlers(application)   # Group 1
    rmamount.register_handlers(application)     # Group 1
    restwithdraw.register_handlers(application) # Group 1
    message_handler.register_handlers(application) # Group 2

    logger.info("Starting bot")
    try:
        application.run_polling(allowed_updates=["message", "callback_query"])
    except Exception as e:
        logger.error(f"Bot crashed: {e}\n{traceback.format_exc()}")
    finally:
        logger.info("Bot stopped")

if __name__ == "__main__":
    main()