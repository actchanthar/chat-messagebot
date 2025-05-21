from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
import logging
from database.database import db
from config import CURRENCY, DEFAULT_REQUIRED_INVITES

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    logger.info(f"Button callback by user {user_id}: {query.data}")

    try:
        user = await db.get_user(user_id)
        if not user:
            await query.message.reply_text("Please start with /start first.")
            return

        if query.data == "balance":
            balance = user.get("balance", 0)
            invited_users = user.get("invited_users", 0) if isinstance(user.get("invited_users"), (int, float)) else len(user.get("invited_users", [])) if isinstance(user.get("invited_users"), list) else 0
            await query.message.reply_text(
                f"Your balance: {balance} {CURRENCY}\n"
                f"Invited users: {invited_users}/{DEFAULT_REQUIRED_INVITES}\n"
                "Use /withdraw to request a withdrawal after joining required channels."
            )
        elif query.data == "withdraw":
            if not user.get("joined_channels", False):
                required_channels = await db.get_required_channels()
                channels_text = "\n".join([channel if channel.startswith("https://") else f"https://t.me/{channel.lstrip('@')}" for channel in required_channels])
                await query.message.reply_text(
                    f"Please join all required channels to withdraw:\n{channels_text}\n"
                    "Then use /checksubscription and try again."
                )
            else:
                await query.message.reply_text("Please use /withdraw to initiate a withdrawal.")
    except Exception as e:
        logger.error(f"Error in button callback for user {user_id}: {e}", exc_info=True)
        try:
            await query.message.reply_text("An error occurred. Please try again or contact @actearnbot.")
        except Exception as reply_e:
            logger.error(f"Failed to send error message to {user_id}: {reply_e}")

def register_handlers(application: Application):
    logger.info("Registering callback handlers")
    application.add_handler(CallbackQueryHandler(button_callback, pattern="^(balance|withdraw)$", block=False))