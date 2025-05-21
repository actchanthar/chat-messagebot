from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import logging
from config import CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if update.effective_chat.type != "private":
        await update.message.reply_text("Please use /transfer in a private chat.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /transfer <user_id> <amount>")
        return

    target_user_id, amount = context.args
    try:
        amount = int(amount)
        if amount <= 0:
            await update.message.reply_text("Amount must be positive.")
            return
        if await db.transfer_balance(user_id, target_user_id, amount):
            await update.message.reply_text(f"Transferred {amount} {CURRENCY} to user {target_user_id}.")
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"You received {amount} {CURRENCY} from {update.effective_user.full_name}!"
            )
        else:
            await update.message.reply_text("Transfer failed. Check user ID or balance.")
    except ValueError:
        await update.message.reply_text("Please provide a valid amount.")

def register_handlers(application):
    logger.info("Registering transfer handlers")
    application.add_handler(CommandHandler("transfer", transfer))