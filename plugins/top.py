from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"User {user_id} requested top users")

    # Get top users
    top_users = await db.get_top_users()
    if not top_users:
        await update.message.reply_text("No top users available yet.")
        logger.warning("No top users found or error retrieving top users")
        return

    # Build the top users message
    top_users_text = "🏆 Top Users:\n"
    for i, user in enumerate(top_users, 1):
        top_users_text += f"{i}. {user['name']}: {user['messages']} စာတို၊ {user.get('balance', 0)} {config.CURRENCY}\n"

    await update.message.reply_text(top_users_text)
    logger.info(f"Sent top users list to user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering top handlers")
    application.add_handler(CommandHandler("top", top))