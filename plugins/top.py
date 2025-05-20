from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Top command initiated by user {user_id} in chat {chat_id}")

    # Check rate limit
    try:
        rate_limit_ok = await db.check_rate_limit(user_id, "top_command")
        if not rate_limit_ok:
            await update.message.reply_text("You are sending commands too quickly. Please wait a moment and try again.")
            logger.info(f"User {user_id} rate limited for top command")
            return
    except Exception as e:
        logger.error(f"Error checking rate limit for user {user_id}: {e}")
        await update.message.reply_text("Error checking rate limit. Please try again later.")
        return

    top_message = "🏆 Top Users\n\n"

    # Fetch top users by invites
    top_users = await db.get_top_users(10, sort_by="invites")
    if top_users and top_users[0].get("invites", 0) > 0:
        phone_bill_reward = await db.get_phone_bill_reward()
        top_message += (
            "Top Users by Invites:\n\n"
            f"(၇ ရက်တစ်ခါ Top 1-3 ရတဲ့လူကို {phone_bill_reward} မဲဖောက်ပေးပါတယ်):\n\n"
        )
        for i, user in enumerate(top_users, 1):
            invites = user.get("invites", 0)
            balance = user.get("balance", 0)
            top_message += f"{i}. <b>{user['name']}</b> - {invites} invites, {balance} kyat\n" if i <= 3 else f"{i}. {user['name']} - {invites} invites, {balance} kyat\n"

    # Fetch top users by messages
    top_users = await db.get_top_users(10, sort_by="messages")
    if top_users and top_users[0].get("group_messages", {}).get("-1002061898677", 0) > 0:
        phone_bill_reward = await db.get_phone_bill_reward()
        top_message += (
            "\nTop Users by Messages:\n\n"
            f"(၇ ရက်တစ်ခါ Top 1-3 ရတဲ့လူကို {phone_bill_reward} မဲဖောက်ပေးပါတယ်):\n\n"
        )
        for i, user in enumerate(top_users, 1):
            messages = user.get("group_messages", {}).get("-1002061898677", 0)
            balance = user.get("balance", 0)
            top_message += f"{i}. <b>{user['name']}</b> - {messages} msg, {balance} kyat\n" if i <= 3 else f"{i}. {user['name']} - {messages} msg, {balance} kyat\n"

    await update.message.reply_text(top_message, parse_mode="HTML")
    logger.info(f"Sent top users list to user {user_id} in chat {chat_id}")

def register_handlers(application: Application):
    logger.info("Registering top handlers")
    application.add_handler(CommandHandler("top", top))