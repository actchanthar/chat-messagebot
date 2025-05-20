from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /transfer <user_id> <amount>")
        return

    target_id, amount = context.args
    try:
        amount = float(amount)
        sender = await db.get_user(user_id)
        receiver = await db.get_user(target_id)

        if not sender or not receiver:
            await update.message.reply_text("Sender or receiver not found.")
            return

        if sender.get("balance", 0) < amount:
            await update.message.reply_text("Insufficient balance.")
            return

        sender_balance = sender.get("balance", 0) - amount
        receiver_balance = receiver.get("balance", 0) + amount
        await db.update_user(user_id, {"balance": sender_balance})
        await db.update_user(target_id, {"balance": receiver_balance})
        await update.message.reply_text(f"Transferred {amount} kyat to user {target_id}.")
        await context.bot.send_message(target_id, f"You received {amount} kyat from user {user_id}.")
    except ValueError:
        await update.message.reply_text("Invalid amount.")

def register_handlers(application: Application):
    logger.info("Registering transfer handlers")
    application.add_handler(CommandHandler("transfer", transfer))