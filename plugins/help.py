from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Admin user ID (replace with your admin's Telegram user ID)
ADMIN_USER_ID = "5062124930"

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Help command initiated by user {user_id}")

    # Check if user is admin
    is_admin = user_id == ADMIN_USER_ID

    help_text = "Available commands:\n\n"
    help_text += "/start - Welcome message and profile creation.\n"
    help_text += "/balance - Check your balance.\n"
    help_text += "/withdraw - Initiate a withdrawal.\n"
    help_text += "/top - Show top users by invites and messages.\n"

    if is_admin:
        help_text += "\nAdmin-only commands:\n"
        help_text += "/rest - Reset message counts.\n"
        help_text += "/addgroup <group_id> - Add group for message counting.\n"
        help_text += "/checkgroup <group_id> - Check group message count.\n"
        help_text += "/SetPhoneBill <reward_text> - Set Phone Bill reward text.\n"
        help_text += "/broadcast <message> - Send message to all users.\n"
        help_text += "/pbroadcast <message> - Send pinned message to all users.\n"
        help_text += "/users - Show total user count.\n"
        help_text += "/addchnl <channel_id> <name> - Add channel for forced subscription.\n"
        help_text += "/delchnl <channel_id> - Remove channel.\n"
        help_text += "/listchnl - List all forced subscription channels.\n"
        help_text += "/setinvite <number> - Set invite threshold for withdrawals.\n"
        help_text += "/Add_bonus <user_id> <amount> - Add bonus to user.\n"
        help_text += "/setmessage <number> - Set messages per kyat.\n"
        help_text += "/debug_message_count - Debug message counts.\n"
        help_text += "/restwithdraw <user_id|ALL> - Reset withdrawal records.\n"
        help_text += "/clone <mongodb_url> - Clone database to new MongoDB URL.\n"
        help_text += "/on - Enable message counting.\n"

    help_text += "\n/referral_users - Show referral stats and link.\n"
    help_text += "/couple - Randomly match two users (10-minute cooldown).\n"
    help_text += "/transfer <user_id> <amount> - Transfer balance to another user.\n"
    help_text += "/checksubscription - Check user's subscription status.\n"

    await update.message.reply_text(help_text)
    logger.info(f"Sent help text to user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering help handlers")
    application.add_handler(CommandHandler("help", help_command))