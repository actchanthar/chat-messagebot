from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import CURRENCY, LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    users = await db.get_all_users()
    total_users = len(users)

    # Top by invites
    top_invites = await db.get_top_users(10, "invites")
    invite_msg = f"Top Users by Invites (Weekly Top 1-3 get Phone Bill gift 🎁: 10000):\nTotal Users: {total_users}\n\n"
    for i, user in enumerate(top_invites, 1):
        invites = user.get("invite_count", 0)
        balance = user.get("balance", 0)
        invite_msg += f"{i}. {'<b>' if i <= 3 else ''}{user['name']}{'</b>' if i <= 3 else ''} - {invites} invites, {balance} {CURRENCY}\n"

    # Top by messages
    top_messages = await db.get_top_users(10, "messages")
    message_msg = f"\n🏆 Top Users (by messages):\n"
    for i, user in enumerate(top_messages, 1):
        messages = user.get("messages", 0)
        balance = user.get("balance", 0)
        message_msg += f"{i}. {'<b>' if i <= 3 else ''}{user['name']}{'</b>' if i <= 3 else ''} - {messages} msg, {balance} {CURRENCY}\n"

    await update.message.reply_text(invite_msg + message_msg, parse_mode="HTML")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("top", top))