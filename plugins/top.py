from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import GROUP_CHAT_IDS, CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"/top command initiated by user {user_id} in chat {chat_id}")

    # Check if the command is in an approved group
    approved_groups = await db.get_approved_groups()
    if str(chat_id) not in approved_groups and chat_id != int(user_id):  # Allow in private chat
        await context.bot.send_message(
            chat_id=chat_id,
            text="ဤအမှာစကားကို အုပ်စုတွင်သာ အသုံးပြုနိုင်ပါသည်။"
        )
        logger.warning(f"User {user_id} attempted /top in unapproved chat {chat_id}")
        return

    # Get top users by messages
    top_users = await db.get_top_users(limit=10, sort_by="messages")
    if not top_users:
        await context.bot.send_message(
            chat_id=chat_id,
            text="ထိပ်တန်းအသုံးပြုသူများ မရှိပါ။"
        )
        logger.warning("No top users found for /top command")
        return

    message = "🏆 Top 10 Users (by messages):\n\n"
    for i, user in enumerate(top_users, 1):
        user_id_from_db = user["user_id"]
        # Fetch user info from Telegram if name is missing
        try:
            telegram_user = await context.bot.get_chat(user_id_from_db)
            first_name = user.get("first_name") or telegram_user.first_name or "Unknown"
            last_name = user.get("last_name") or telegram_user.last_name or ""
            # Update the database with the user's name if missing
            if not user.get("first_name") or not user.get("last_name"):
                await db.update_user(user_id_from_db, {
                    "first_name": telegram_user.first_name,
                    "last_name": telegram_user.last_name
                })
        except Exception as e:
            logger.error(f"Failed to fetch user info for {user_id_from_db}: {e}")
            first_name = user.get("first_name", "Unknown")
            last_name = user.get("last_name", "")

        name = f"{first_name} {last_name}".strip() or str(user_id_from_db)
        messages = user.get("messages", 0)
        balance = user.get("balance", 0)
        message += f"{i}. {name} ({user['user_id']}): {messages} msg, {int(balance)} {CURRENCY}\n"

    await context.bot.send_message(chat_id=chat_id, text=message)
    logger.info(f"Sent top 10 users to user {user_id} in chat {chat_id}")

def register_handlers(application: Application):
    logger.info("Registering top handlers")
    application.add_handler(CommandHandler("top", top))