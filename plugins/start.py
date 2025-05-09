from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
import config
from database import db

async def start_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        f'Welcome to Chat Activity Reward Bot!\n\n'
        f'For every message you send, you get {config.REWARD_PER_MESSAGE} {config.CURRENCY}.\n'
        f'Spam messages will not be counted.\n\n'
        f'Commands:\n'
        f'/balance - Check your current balance\n'
        f'/stats - View chat statistics\n'
        f'/help - Show this help message'
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        f'Chat Activity Reward Bot helps you earn rewards for being active in the chat.\n\n'
        f'For every valid message you send, you earn {config.REWARD_PER_MESSAGE} {config.CURRENCY}.\n'
        f'Spam messages (repeating the same content) will not be counted.\n\n'
        f'Commands:\n'
        f'/balance - Check your current balance\n'
        f'/stats - View chat statistics\n'
        f'/help - Show this help message'
    )

def register_handlers(application):
    """Register handlers for this plugin"""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))