from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from config import BOT_USERNAME

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Help command by user {user_id} in chat {chat_id}")

    help_text = (
        f"Welcome to {BOT_USERNAME}!\n"
        "Here are the available commands:\n\n"
        "/start - Start the bot\n"
        "/top - Show leaderboards (invites and messages)\n"
        "/withdraw - Withdraw earnings\n"
        "/referral_users - Check referral stats\n"
        "/balance - Check balance\n"
        "/transfer - Transfer balance to another user\n"
        "/couple - Join random pairing every 10 minutes\n"
        "/users - Show user stats (admin only)\n"
        "/addgroup - Add group for message counting (admin only)\n"
        "/checkgroup - Check group message counts (admin only)\n"
        "/setphonebill - Set Phone Bill reward text (admin only)\n"
        "/rest - Reset leaderboards (admin only)\n"
        "/broadcast - Send message to all users (admin only)\n"
        "/pbroadcast - Send and pin message to all users (admin only)\n"
        "/addchnl - Add channel for force-subscription (admin only)\n"
        "/delchnl - Remove channel from force-subscription (admin only)\n"
        "/listchnl - List force-subscription channels (admin only)\n"
        "/Add_bonus - Add bonus to user (admin only)\n"
        "/restwithdraw - Reset pending withdrawals (admin only)\n"
        "/setinvite - Set invite requirement (admin only)\n"
        "/setmessage - Set messages per kyat (admin only)"
    )

    await update.message.reply_text(help_text)
    logger.info(f"Sent help text to user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering help handler")
    application.add_handler(CommandHandler("help", help_command))