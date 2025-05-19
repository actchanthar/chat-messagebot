from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /transfer <target_id> <amount>")
        return

    target_id, amount = context.args[0], int(context.args[1])
    user = await db.get_user(user_id)
    target = await db.get_user(target_id)

    if not target:
        await update.message.reply_text("Target user not found.")
        return
    if user["balance"] < amount:
        await update.message.reply_text("Insufficient balance.")
        return

    await db.update_user(user_id, {"balance": user["balance"] - amount})
    await db.update_user(target_id, {"balance": target["balance"] + amount})
    await update.message.reply_text(f"Transferred {amount} kyat to {target['name']}.")
    await context.bot.send_message(target_id, f"You received {amount} kyat from {user['name']}.")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("transfer", transfer))