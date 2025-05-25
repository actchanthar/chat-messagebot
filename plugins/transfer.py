from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import CURRENCY, LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Transfer command by user {user_id} in chat {chat_id}")

    if chat_id != user_id:
        await update.message.reply_text("Please use /transfer in a private chat.")
        logger.info(f"User {user_id} attempted transfer in non-private chat {chat_id}")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /transfer <user_id> <amount>")
        logger.info(f"Insufficient arguments for transfer by user {user_id}")
        return

    try:
        target_user_id = context.args[0]
        amount = float(context.args[1])
        if amount <= 0:
            await update.message.reply_text("Amount must be positive.")
            return

        if target_user_id == user_id:
            await update.message.reply_text("You cannot transfer to yourself.")
            return

        user = await db.get_user(user_id)
        if not user or user.get("balance", 0) < amount:
            await update.message.reply_text("Insufficient balance or user not found.")
            logger.info(f"Insufficient balance for user {user_id}: {user.get('balance', 0)} < {amount}")
            return

        success = await db.transfer_balance(user_id, target_user_id, amount)
        if success:
            from_user = await db.get_user(user_id)
            to_user = await db.get_user(target_user_id)
            from_balance = from_user.get("balance", 0)
            to_balance = to_user.get("balance", 0)
            await update.message.reply_text(
                f"Transferred {amount} {CURRENCY} to user {target_user_id}. "
                f"Your new balance: {from_balance} {CURRENCY}."
            )
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"You received {amount} {CURRENCY} from user {user_id}. "
                     f"Your new balance: {to_balance} {CURRENCY}."
            )
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"User {user_id} transferred {amount} {CURRENCY} to user {target_user_id}."
            )
            logger.info(f"User {user_id} transferred {amount} {CURRENCY} to {target_user_id}")
        else:
            await update.message.reply_text("Failed to transfer. Target user not found or insufficient balance.")
            logger.error(f"Failed to transfer {amount} {CURRENCY} from {user_id} to {target_user_id}")
    except ValueError:
        await update.message.reply_text("Invalid amount. Please provide a number.")
        logger.error(f"Invalid amount provided by user {user_id}: {context.args[1]}")
    except Exception as e:
        await update.message.reply_text("An error occurred. Please try again.")
        logger.error(f"Error in transfer for user {user_id} to {target_user_id}: {e}")

def register_handlers(application: Application):
    logger.info("Registering transfer handler")
    application.add_handler(CommandHandler("transfer", transfer))