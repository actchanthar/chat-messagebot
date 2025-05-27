from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import ADMIN_IDS
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def rmamount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"rmamount command initiated by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        logger.info(f"User {user_id} attempted rmamount but is not an admin")
        await update.message.reply_text("This command is restricted to admins.")
        return

    args = context.args
    if args and len(args) == 1:
        target_user_id = args[0]
        logger.info(f"Resetting withdrawn_today for user {target_user_id}")
        user = await db.get_user(target_user_id)
        if not user:
            logger.error(f"User {target_user_id} not found")
            await update.message.reply_text(f"User {target_user_id} not found.")
            return
        try:
            await db.update_user(target_user_id, {
                "withdrawn_today": 0,
                "last_withdrawal": None
            })
            logger.info(f"Successfully reset withdrawn_today for user {target_user_id}")
            await update.message.reply_text(f"Successfully reset withdrawn amount for user {target_user_id}.")
        except Exception as e:
            logger.error(f"Failed to reset withdrawn_today for user {target_user_id}: {e}")
            await update.message.reply_text(f"Error resetting withdrawn amount for user {target_user_id}.")
    else:
        logger.info("Resetting withdrawn_today for all users")
        try:
            result = await db.users.update_many(
                {},
                {"$set": {"withdrawn_today": 0, "last_withdrawal": None}}
            )
            logger.info(f"Successfully reset withdrawn_today for {result.modified_count} users")
            await update.message.reply_text(f"Successfully reset withdrawn amount for {result.modified_count} users.")
        except Exception as e:
            logger.error(f"Failed to reset withdrawn_today for all users: {e}")
            await update.message.reply_text("Error resetting withdrawn amounts for all users.")

def register_handlers(application: Application):
    logger.info("Registering rmamount handlers")
    application.add_handler(CommandHandler("rmamount", rmamount))