from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if await db.check_rate_limit(user_id):
        await update.message.reply_text("Please wait before using this command again.")
        logger.warning(f"Rate limit hit for /top by user {user_id}")
        return

    try:
        # Award weekly rewards if due
        if await db.award_weekly_rewards():
            await update.message.reply_text("Weekly rewards of 10000 kyat awarded to top 3 inviters!")
            logger.info(f"Weekly rewards awarded by user {user_id}")

        # Get total users
        users = await db.get_all_users()
        total_users = len(users) if users else 0

        # Get top users
        top_invites = await db.get_top_users(by="invites", limit=10)
        top_messages = await db.get_top_users(by="messages", limit=10)

        # Format message
        message = (
            "Top Users by Invites (၇ ရက်တစ်ခါ Top 1-3 ကို ဖုန်းဘေ လက်ဆောင် ပေးပါတယ် 🎁: 10000):\n\n"
            f"Total Users: {total_users}\n\n"
        )
        if top_invites:
            for i, user in enumerate(top_invites, 1):
                invites = user.get("invite_count", 0)
                balance = user.get("balance", 0)
                message += f"{i}. {user['name']} - {invites} invites, {balance:.2f} kyat\n"
        else:
            message += "No users with invites yet.\n"

        message += "\nTop Users by Messages:\n\n"
        if top_messages:
            for i, user in enumerate(top_messages, 1):
                messages = user.get("messages", 0)
                balance = user.get("balance", 0)
                message += f"{i}. {user['name']} - {messages} msg, {balance:.2f} kyat\n"
        else:
            message += "No users with messages yet.\n"

        await update.message.reply_text(message)
        logger.info(f"User {user_id} executed /top successfully")
    except Exception as e:
        await update.message.reply_text("Failed to fetch top users. Please try again later.")
        logger.error(f"Error in /top for user {user_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("top", top))