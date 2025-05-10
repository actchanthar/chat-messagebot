from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Chat Group Management Bot!\n\n"
        "Earn 1 kyat per valid message.\n"
        "Commands:\n"
        "/balance - Check earnings\n"
        "/top - View top users\n"
        "/withdraw - Request withdrawal\n"
        "/help - Show this message"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Earn 1 kyat per valid message.\n"
        "Join our channel to withdraw.\n\n"
        "Commands:\n"
        "/balance - Check earnings\n"
        "/top - View top users\n"
        "/withdraw - Request withdrawal\n"
        "/help - Show this message"
    )

def register_handlers(application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))