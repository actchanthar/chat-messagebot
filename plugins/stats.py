from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
import config
from database import db

async def stats_command(update: Update, context: CallbackContext) -> None:
    """Show chat statistics."""
    # Get top users from database
    top_users = await db.get_top_users(limit=10)
    
    if not top_users:
        await update.message.reply_text("No statistics available yet.")
        return
    
    # Get overall stats
    all_stats = await db.get_all_stats()
    
    # Create message with top 10 users
    message = "📊 Chat Activity Statistics 📊\n\n"
    message += "Top Active Users:\n"
    
    for i, user in enumerate(top_users, 1):
        message += f"{i}. {user['name']}: {user['messages']} messages, {user['balance']} {config.CURRENCY}\n"
    
    message += f"\nTotal group activity: {all_stats['total_messages']} messages"
    message += f"\nTotal rewards distributed: {all_stats['total_balance']} {config.CURRENCY}"
    
    await update.message.reply_text(message)

def register_handlers(application):
    """Register handlers for this plugin"""
    application.add_handler(CommandHandler("stats", stats_command))