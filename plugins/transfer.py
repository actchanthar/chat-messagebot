from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /transfer <target_user_id> <amount>")
        return

    target_user_id = context.args[0]
    try:
        amount = int(context.args[1])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please provide a valid positive amount.")
        return

    user = await db.get_user(user_id)
    if not user or user.get("balance", 0) < amount:
        await update.message.reply_text("Insufficient balance.")
        return

    target_user = await db.get_user(target_user_id)
    if not target_user:
        await update.message.reply_text("Target user not found.")
        return

    await db.update_user(user_id, {"balance": user.get("balance", 0) - amount})
    await db.update_user(target_user_id, {"balance": target_user.get("balance", 0) + amount})
    await update.message.reply_text(f"Transferred {amount} {CURRENCY} to user {target_user_id}.")
    await context.bot.send_message(
        chat_id=target_user_id,
        text=f"You received {amount} {CURRENCY} from user {user_id}."
    )

def register_handlers(application: Application):
    logger.info("Registering transfer handlers")
    application.add_handler(CommandHandler("transfer", transfer))