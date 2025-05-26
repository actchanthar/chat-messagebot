from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Received /help command from user {user_id} in chat {chat_id}")

    reply_func = update.message.reply_text if update.message else update.callback_query.message.reply_text

    commands = (
        "Available Commands:\n"
        "/start - Start the bot and set up your profile\n"
        "/balance - Check your current balance\n"
        "/top - View top 10 users by messages or invites\n"
        "/withdraw - Request a withdrawal of your earnings\n"
        "/couple - Find a random couple match\n"
        "/transfer <user_id> <amount> - Transfer balance to another user\n"
        "/help - Show this help message\n\n"
        "Admin Commands:\n"
        "/addgroup <group_id> - Add a group for message counting\n"
        "/checkgroup <group_id> - Check group message count\n"
        "/setphonebill <reward_text> - Set Phone Bill reward text\n"
        "/addchnl <channel_id> <channel_name> - Add a channel for force subscription\n"
        "/delchnl <channel_id> - Remove a channel from force subscription\n"
        "/listchnl - List all force subscription channels\n"
        "/broadcast <message> - Send a message to all users\n"
        "/pbroadcast <message> - Send a pinned message to all users\n"
        "/rest - Reset message counts\n"
        "/add_bonus <user_id> <amount> - Add bonus to a user\n"
        "/setmessage <number> - Set messages per kyat\n"
        "/restwithdraw <user_id or ALL> - Reset pending withdrawals\n"
        "/setinvite <number> - Set required invites for withdrawal"
    )
    await reply_func(commands)
    logger.info(f"Sent help response to user {user_id} in chat {chat_id}")

def register_handlers(application):
    logger.info("Registering help handlers")
    application.add_handler(CommandHandler("help", help_command))