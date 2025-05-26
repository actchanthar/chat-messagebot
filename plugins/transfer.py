from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import CURRENCY, LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Transfer command initiated by user {user_id} in chat {chat_id}")

    if update.effective_chat.type != "private":
        await update.message.reply_text("Please use the /transfer command in a private chat.")
        logger.info(f"User {user_id} attempted transfer in non-private chat {chat_id}")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /transfer <user_id> <amount>")
        logger.info(f"Invalid transfer arguments by user {user_id}")
        return

    try:
        to_user_id = str(context.args[0])
        amount = float(context.args[1])
        if amount <= 0:
            await update.message.reply_text("Amount must be greater than 0.")
            logger.info(f"Invalid transfer amount {amount} by user {user_id}")
            return

        success = await db.transfer_balance(user_id, to_user_id, amount)
        if success:
            user = await db.get_user(user_id)
            to_user = await db.get_user(to_user_id)
            await update.message.reply_text(
                f"Successfully transferred {amount} {CURRENCY} to user {to_user['name']}.\n"
                f"Your new balance: {user['balance']} {CURRENCY}"
            )
            await context.bot.send_message(
                chat_id=to_user_id,
                text=f"You received {amount} {CURRENCY} from {user['name']}.\nYour new balance: {to_user['balance']} {CURRENCY}"
            )
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Transfer: {user['name']} ({user_id}) sent {amount} {CURRENCY} to {to_user['name']} ({to_user_id})"
            )
            logger.info(f"User {user_id} transferred {amount} {CURRENCY} to {to_user_id}")
        else:
            await update.message.reply_text("Transfer failed. Check user ID or balance.")
            logger.error(f"Transfer failed for user {user_id} to {to_user_id}")
    except ValueError:
        await update.message.reply_text("Please enter a valid number for the amount.")
        logger.info(f"Invalid amount format by user {user_id}")
    except Exception as e:
        await update.message.reply_text("An error occurred. Please try again.")
        logger.error(f"Error in transfer for user {user_id}: {e}")

def register_handlers(application: Application):
    logger.info("Registering transfer handlers")
    application.add_handler(CommandHandler("transfer", transfer))