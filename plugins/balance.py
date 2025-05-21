from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import CURRENCY, REQUIRED_CHANNELS
import asyncio

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Balance command by user {user_id}")

    try:
        user = await db.get_user(user_id)
        if not user:
            for attempt in range(3):
                user = await db.create_user(user_id, update.effective_user.full_name or "Unknown")
                if user:
                    break
                logger.warning(f"Attempt {attempt + 1} failed to create user {user_id}")
                await asyncio.sleep(0.5)
            if not user:
                logger.error(f"Failed to create user {user_id} after 3 attempts")
                try:
                    await update.message.reply_text("Please start with /start first.")
                except Exception as e:
                    logger.error(f"Failed to send user not found message to {user_id}: {e}")
                return

        await db.update_user(user_id, {"username": update.effective_user.username})

        balance = user.get("balance", 0)
        invited_users = user.get("invited_users", 0) if isinstance(user.get("invited_users"), (int, float)) else len(user.get("invited_users", [])) if isinstance(user.get("invited_users"), list) else 0
        invite_requirement = await db.get_setting("invite_requirement", 15)
        channels_joined = user.get("joined_channels", False)

        message = (
            f"Your balance: {balance} {CURRENCY}\n"
            f"Invited users: {invited_users}/{invite_requirement}\n"
        )
        if not channels_joined:
            channels_text = "\n".join([f"https://t.me/{channel.lstrip('@')}" for channel in await db.get_required_channels()])
            message += (
                f"Please join all required channels to withdraw:\n{channels_text}\n"
                "Then use /checksubscription."
            )
        else:
            message += "Use /withdraw to request a withdrawal."

        try:
            await update.message.reply_text(message)
            logger.info(f"Sent balance to user {user_id}: {balance} {CURRENCY}, {invited_users}/{invite_requirement} invites")
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to send balance message to {user_id}: {e}")
    except Exception as e:
        logger.error(f"Error in balance for user {user_id}: {e}", exc_info=True)
        try:
            await update.message.reply_text("An error occurred. Please try again or contact @actearnbot.")
        except Exception as e2:
            logger.error(f"Failed to send error message to {user_id}: {e2}")

def register_handlers(application: Application):
    logger.info("Registering balance handlers")
    application.add_handler(CommandHandler("balance", balance, block=False))