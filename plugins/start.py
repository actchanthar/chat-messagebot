from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Define inline keyboard buttons
    keyboard = [
        [
            InlineKeyboardButton("Withdrawal", callback_data="withdraw"),
            InlineKeyboardButton("Balance", callback_data="balance"),
        ],
        [
            InlineKeyboardButton("Top", callback_data="top"),
            InlineKeyboardButton("Help", callback_data="help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send welcome message with image and buttons
    await update.message.reply_photo(
        photo="https://i.imghippo.com/files/cbg1841XQ.jpg",
        caption=(
            "Welcome to Chat Group Management Bot!\n\n"
            "Earn 1 kyat per valid message.\n"
            "Commands:\n"
            "/balance - Check earnings\n"
            "/top - View top users\n"
            "/withdraw - Request withdrawal\n"
            "/help - Show this message"
        ),
        reply_markup=reply_markup
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