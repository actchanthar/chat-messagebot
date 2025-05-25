from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import ADMIN_IDS, LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def restwithdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Restwithdraw command by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized restwithdraw attempt by user {user_id}")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    target_user_id = context.args[0] if context.args else None
    success = await db.reset_withdrawals(target_user_id)
    
    if success:
        if target_user_id:
            await update.message.reply_text(f"Pending withdrawals reset for user {target_user_id}.")
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Admin {user_id} reset pending withdrawals for user {target_user_id}."
            )
            logger.info(f"Reset pending withdrawals for user {target_user_id} by admin {user_id}")
        else:
            await update.message.reply_text("All pending withdrawals reset.")
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Admin {user_id} reset all pending withdrawals."
            )
            logger.info(f"Reset all pending withdrawals by admin {user_id}")
    else:
        await update.message.reply_text("Failed to reset withdrawals. Please try again.")
        logger.error(f"Failed to reset withdrawals for user {target_user_id} by admin {user_id}")

def register_handlers(application: Application):
    logger.info("Registering restwithdraw handler")
    application.add_handler(CommandHandler("restwithdraw", restwithdraw))