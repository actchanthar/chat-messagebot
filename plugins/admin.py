from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import RetryAfter
from database.database import db
import config
import logging

logger = logging.getLogger(__name__)

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

async def add_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("Admins only.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /add_bonus <user_id> <amount>")
        return
    
    target_user_id = context.args[0]
    try:
        amount = float(context.args[1])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Amount must be a positive number.")
        return
    
    user = await db.get_user(target_user_id)
    if not user:
        await db.create_user(target_user_id, "Unknown")
        user = await db.get_user(target_user_id)
    
    await db.add_bonus(target_user_id, amount)
    await update.message.reply_text(
        f"Added {amount} {config.CURRENCY} bonus to {user['name']} (ID: {target_user_id})."
    )

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in config.ADMIN_IDS:
        return
    
    if not update.message.reply_to_message:
        return
    
    # Check if replying to a withdrawal request
    reply_text = update.message.reply_to_message.text or update.message.reply_to_message.caption or ""
    if "Withdrawal Request" not in reply_text:
        return
    
    # Extract user_id from the withdrawal request
    lines = reply_text.split("\n")
    target_user_id = None
    amount = None
    for line in lines:
        if line.startswith("User ID: "):
            target_user_id = line.split("User ID: ")[1]
        if line.startswith("Amount: "):
            amount = line.split("Amount: ")[1].split(f" {config.CURRENCY}")[0]
    
    if not target_user_id or not amount:
        await update.message.reply_text("Could not parse withdrawal request.")
        return
    
    user = await db.get_user(target_user_id)
    if not user:
        await update.message.reply_text(f"User {target_user_id} not found.")
        return
    
    # Send receipt to user
    try:
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=target_user_id,
                photo=update.message.photo[-1].file_id,
                caption=f"Your withdrawal of {amount} {config.CURRENCY} has been processed."
            )
        else:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"Your withdrawal of {amount} {config.CURRENCY} has been processed."
            )
        await update.message.reply_text(f"Receipt sent to {user['name']} (ID: {target_user_id}).")
        
        # Reset balance after successful withdrawal
        await db.reset_balance(target_user_id)
    except RetryAfter as e:
        logger.warning(f"RetryAfter error for user {target_user_id}: {e}")
        await update.message.reply_text(f"Failed to send receipt due to rate limits. Try again later.")
    except Exception as e:
        logger.error(f"Failed to send receipt to {target_user_id}: {e}")
        await update.message.reply_text(f"Failed to send receipt: {e}")

def register_handlers(application):
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("pay", pay))
    application.add_handler(CommandHandler("add_bonus", add_bonus))
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.TEXT & ~filters.COMMAND & filters.REPLY,
        handle_receipt
    ))