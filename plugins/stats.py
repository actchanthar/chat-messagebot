from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database.database import db
import config

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = await db.get_top_users()
    if not top_users:
        await update.message.reply_text("No stats yet.")
        return
    
    message = "🏆 Top Users 🏆\n"
    for i, user in enumerate(top_users, 1):
        message += f"{i}. {user['name']}: {user['messages']} messages, {user['balance']} {config.CURRENCY}\n"
    
    total_messages = sum(user['messages'] for user in top_users)
    total_balance = sum(user['balance'] for user in top_users)
    message += f"\nTotal Messages: {total_messages}\nTotal Rewards: {total_balance} {config.CURRENCY}"
    
    await update.message.reply_text(message)

def register_handlers(application):
    application.add_handler(CommandHandler("top", stats))
