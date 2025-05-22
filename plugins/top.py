from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
import time

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if await db.check_rate_limit(user_id):
        await update.message.reply_text("Please wait before using this command again.")
        return

    start_time = time.time()
    try:
        if await db.award_weekly_rewards():
            await update.message.reply_text("Weekly rewards of 10000 kyat awarded to top 3 inviters!")

        total_users = await db.get_total_users()
        top_invites = await db.get_top_users(by="invites", limit=5)
        top_messages = await db.get_top_users(by="messages", limit=10)

        message = (
            "Top Users by Invites (၇ ရက်တစ်ခါ Top 1-3 ကို ဖုန်းဘေ လက်ဆောင် ပေးပါတယ် 🎁: 10000):\n\n"
            f"Total Users: {total_users}\n\n"
        )
        if top_invites:
            for i, user in enumerate(top_invites, 1):
                message += f"{i}. {user['name']} (@{user.get('username', 'N/A')}) - {user.get('invite_count', 0)} invites, {user.get('balance', 0):.2f} kyat\n"
        else:
            message += "No users with invites yet.\n"

        message += "\nTop Users by Messages:\n\n"
        if top_messages:
            for i, user in enumerate(top_messages, 1):
                message += f"{i}. {user['name']} (@{user.get('username', 'N/A')}) - {user.get('messages', 0)} msg, {user.get('balance', 0):.2f} kyat\n"
        else:
            message += "No users with messages yet.\n"

        await update.message.reply_text(message)
        logger.info(f"User {user_id} executed /top in {time.time() - start_time:.2f}s, invites: {len(top_invites)}, messages: {len(top_messages)}")
    except Exception as e:
        await update.message.reply_text("Failed to fetch top users.")
        logger.error(f"Error in /top for user {user_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("top", top))