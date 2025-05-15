from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import CURRENCY, LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Top command initiated by user {user_id} in chat {chat_id}")

    top_users = await db.get_top_users()
    if not top_users:
        await update.message.reply_text("No top users available yet.")
        logger.warning(f"No top users found for user {user_id}")
        return

    top_message = "🏆 Top Users:\n"
    for i, user in enumerate(top_users, 1):
        messages = user.get("messages", 0)
        balance = user.get("balance", 0)
        top_message += f"{i}. {user['name']}: {messages} စာတို၊ {balance} {CURRENCY}\n"

    await update.message.reply_text(top_message)
    logger.info(f"Sent top users list to user {user_id} in chat {chat_id}")

async def rest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Rest command initiated by user {user_id} in chat {chat_id}")

    # Check if the user is an admin (e.g., user_id 5062124930)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized rest attempt by user {user_id}")
        return

    # Reset messages to 0 for all users, keeping balance intact
    result = await db.users.update_many({}, {"$set": {"messages": 0}})
    if result.modified_count > 0:
        await update.message.reply_text("Leaderboard has been reset. Messages set to 0, balances preserved.")
        logger.info(f"Reset messages for {result.modified_count} users by admin {user_id}")

        # Log the action to the admin channel
        current_top = await db.get_top_users()
        log_message = "Leaderboard reset by admin:\n🏆 Top Users (before reset):\n"
        for i, user in enumerate(current_top, 1):
            balance = user.get("balance", 0)
            log_message += f"{i}. {user['name']}: 0 စာတို၊ {balance} {CURRENCY}\n"
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_message)
    else:
        await update.message.reply_text("No users found to reset.")
        logger.info(f"No users modified during reset by user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering top and rest handlers")
    application.add_handler(CommandHandler("top", top))
    application.add_handler(CommandHandler("rest", rest))