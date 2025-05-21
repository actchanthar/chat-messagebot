from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import CURRENCY, DEFAULT_REQUIRED_INVITES

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Balance command by user {user_id}")

    try:
        user = await db.get_user(user_id)
        if not user:
            await update.message.reply_text("Please start with /start first.")
            return

        balance = user.get("balance", 0)
        invited_users = user.get("invited_users", 0) if isinstance(user.get("invited_users"), (int, float)) else len(user.get("invited_users", [])) if isinstance(user.get("invited_users"), list) else 0
        await update.message.reply_text(
            f"Your balance: {balance} {CURRENCY}\n"
            f"Invited users: {invited_users}/{DEFAULT_REQUIRED_INVITES}\n"
            "Use /withdraw to request a withdrawal after joining required channels."
        )
    except Exception as e:
        logger.error(f"Error in balance for user {user_id}: {e}", exc_info=True)
        try:
            await update.message.reply_text("An error occurred. Please try again or contact @actearnbot.")
        except Exception as reply_e:
            logger.error(f"Failed to send error message to {user_id}: {reply_e}")

def register_handlers(application: Application):
    logger.info("Registering balance handlers")
    application.add_handler(CommandHandler("balance", balance, block=False))