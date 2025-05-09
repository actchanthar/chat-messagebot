from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
import logging
import config
from database import db

logger = logging.getLogger(__name__)

def is_admin(user_id):
    """Check if user is an admin"""
    return str(user_id) in config.ADMIN_IDS

async def reset_command(update: Update, context: CallbackContext) -> None:
    """Reset all statistics (admin only)."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("You don't have permission to use this command.")
        return
    
    # Reset all stats
    await db.reset_all_stats()
    await update.message.reply_text("All statistics have been reset.")
    logger.info(f"Admin {user_id} reset all statistics")

async def pay_command(update: Update, context: CallbackContext) -> None:
    """Mark a user as paid (admin only)."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("You don't have permission to use this command.")
        return
    
    # Check if a user ID was provided
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Usage: /pay [user_id]")
        return
    
    target_user_id = context.args[0]
    
    # Get user data
    user = await db.get_user(target_user_id)
    
    if not user:
        await update.message.reply_text(f"User {target_user_id} not found.")
        return
    
    # Reset user's balance to 0 (mark as paid)
    username = user['name']
    amount = user['balance']
    
    # Update user in database
    await db.reset_user_balance(target_user_id)
    
    await update.message.reply_text(
        f"Payment of {amount} {config.CURRENCY} to {username} (ID: {target_user_id}) has been processed."
    )
    logger.info(f"Admin {user_id} processed payment of {amount} for user {target_user_id}")

def register_handlers(application):
    """Register handlers for this plugin"""
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("pay", pay_command))