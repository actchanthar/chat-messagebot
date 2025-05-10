from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import config

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("Admins only.")
        return
    await db.reset_stats()
    await update.message.reply_text("Stats reset.")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("Admins only.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /pay <user_id>")
        return
    
    target_user_id = context.args[0]
    user = await db.get_user(target_user_id)
    if not user:
        await update.message.reply_text(f"User {target_user_id} not found.")
        return
    
    await db.reset_balance(target_user_id)
    await update.message.reply_text(
        f"Paid {user['name']} (ID: {target_user_id}) {user['balance']} {config.CURRENCY}."
    )

def register_handlers(application):
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("pay", pay))