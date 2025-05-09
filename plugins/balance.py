from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
import config
from database import db

async def balance_command(update: Update, context: CallbackContext) -> None:
    """Show user balance."""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    # Get user data from database
    user = await db.get_user(user_id)
    
    if not user:
        # Create new user if not exists
        user = await db.create_or_update_user(user_id, {
            "user_id": user_id,
            "name": user_name,
            "messages": 0,
            "balance": 0
        })
    
    await update.message.reply_text(
        f"Hi {user['name']}!\n"
        f"Your current balance: {user['balance']} {config.CURRENCY}\n"
        f"Total messages: {user['messages']}"
    )

def register_handlers(application):
    """Register handlers for this plugin"""
    application.add_handler(CommandHandler("balance", balance_command))