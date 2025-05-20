from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized.")
        return

    try:
        users = await db.get_all_users()
        total_users = len(users)
        if not users:
            await update.message.reply_text("No users found.")
            return

        # Show total count and optionally list users
        message = f"Total Users: {total_users}\n\n"
        if context.args and context.args[0].lower() == "list":
            message += "User IDs:\n"
            for user in users:
                message += f"- {user['user_id']} ({user['name']})\n"
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in users command for user {user_id}: {e}")
        await update.message.reply_text("An error occurred while fetching users.")

def register_handlers(application: Application):
    logger.info("Registering users handlers")
    application.add_handler(CommandHandler("users", users, block=False))