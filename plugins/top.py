from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        top_invites = await db.get_top_users(by="invites", limit=10)
        top_messages = await db.get_top_users(by="messages", limit=10)
        total_users = await db.get_total_users()

        message = (
            "Top Users by Invites (၇ ရက်တစ်ခါ Top 1-3 ကို ဖုန်းဘေ လက်ဆောင် ပေးပါတယ် 🎁: 10000):\n\n"
            f"Total Users: {total_users}\n\n"
        )

        if not top_invites:
            message += "No users with invites yet.\n"
        else:
            message += "Top Inviters:\n"
            for i, user in enumerate(top_invites, 1):
                name = user.get("name", "Unknown")
                invites = user.get("invite_count", 0)
                message += f"{i}. {name} - {invites} invites\n"

        message += "\nTop Users by Messages:\n"
        if not top_messages:
            message += "No users with messages yet.\n"
        else:
            for i, user in enumerate(top_messages, 1):
                name = user.get("name", "Unknown")
                messages = user.get("messages", 0)
                balance = user.get("balance", 0)
                message += f"{i}. {name} - {messages} msg, {balance:.2f} kyat\n"

        await update.message.reply_text(message)
        logger.info(f"User {update.effective_user.id} requested top users")
    except Exception as e:
        await update.message.reply_text("Failed to retrieve top users.")
        logger.error(f"Error retrieving top users for user {update.effective_user.id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("top", top))