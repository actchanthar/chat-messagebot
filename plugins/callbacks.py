from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
import logging
from database.database import db
from config import CURRENCY, REQUIRED_CHANNELS
import asyncio

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    logger.info(f"Button callback by user {user_id}: {data}")

    try:
        await query.answer()
        user = await db.get_user(user_id)
        if not user:
            for attempt in range(3):
                user = await db.create_user(user_id, query.from_user.full_name or "Unknown")
                if user:
                    break
                logger.warning(f"Attempt {attempt + 1} failed to create user {user_id}")
                await asyncio.sleep(0.5)
            if not user:
                logger.error(f"Failed to create user {user_id} after 3 attempts")
                try:
                    await query.message.reply_text("Please start with /start first.")
                except Exception as e:
                    logger.error(f"Failed to send user not found message to {user_id}: {e}")
                return

        await db.update_user(user_id, {"username": query.from_user.username})

        if data == "balance":
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
                await query.message.reply_text(message)
                logger.info(f"Sent balance to user {user_id}: {balance} {CURRENCY}, {invited_users}/{invite_requirement} invites")
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Failed to send balance message to {user_id}: {e}")
        elif data == "withdraw":
            from withdrawal import withdraw
            await withdraw(update, context)
    except Exception as e:
        logger.error(f"Error in button callback for user {user_id}: {e}", exc_info=True)
        try:
            await query.message.reply_text("An error occurred. Please try again or contact @actearnbot.")
        except Exception as e2:
            logger.error(f"Failed to send error message to {user_id}: {e2}")

def register_handlers(application: Application):
    logger.info("Registering callback handlers")
    application.add_handler(CallbackQueryHandler(button_callback, pattern="^(balance|withdraw)$", block=False))