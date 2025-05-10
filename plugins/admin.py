from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
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

async def handle_withdrawal_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if user_id not in config.ADMIN_IDS:
        await query.message.reply_text("Admins only.")
        return
    
    data = query.data
    if not data.startswith("withdraw_"):
        return
    
    action, target_user_id = data.split("_")[1], data.split("_")[2]
    
    user = await db.get_user(target_user_id)
    if not user:
        await query.message.reply_text(f"User {target_user_id} not found.")
        return
    
    # Extract amount from the original message
    original_message = query.message.text or query.message.caption or ""
    amount = None
    for line in original_message.split("\n"):
        if line.startswith("Amount: "):
            amount = line.split("Amount: ")[1].split(f" {config.CURRENCY}")[0]
            break
    
    if not amount:
        await query.message.reply_text("Could not parse withdrawal amount.")
        return
    
    try:
        amount = float(amount)
    except ValueError:
        await query.message.reply_text("Invalid withdrawal amount.")
        return
    
    if action == "approve":
        # Send confirmation to user (with receipt if available)
        try:
            if query.message.photo:
                await context.bot.send_photo(
                    chat_id=target_user_id,
                    photo=query.message.photo[-1].file_id,
                    caption=f"Your withdrawal of {amount} {config.CURRENCY} has been approved."
                )
            else:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"Your withdrawal of {amount} {config.CURRENCY} has been approved."
                )
            await query.message.reply_text(
                f"Approved withdrawal for {user['name']} (ID: {target_user_id})."
            )
            # Reset balance after approval
            await db.reset_balance(target_user_id)
        except RetryAfter as e:
            logger.warning(f"RetryAfter error for user {target_user_id}: {e}")
            await query.message.reply_text("Failed to notify user due to rate limits.")
        except Exception as e:
            logger.error(f"Failed to notify user {target_user_id}: {e}")
            await query.message.reply_text(f"Failed to notify user: {e}")
    
    elif action == "reject":
        # Notify user of rejection
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"Your withdrawal request of {amount} {config.CURRENCY} was rejected."
            )
            await query.message.reply_text(
                f"Rejected withdrawal for {user['name']} (ID: {target_user_id})."
            )
        except RetryAfter as e:
            logger.warning(f"RetryAfter error for user {target_user_id}: {e}")
            await query.message.reply_text("Failed to notify user due to rate limits.")
        except Exception as e:
            logger.error(f"Failed to notify user {target_user_id}: {e}")
            await query.message.reply_text(f"Failed to notify user: {e}")
    
    # Remove buttons after action
    await query.message.edit_reply_markup(reply_markup=None)

def register_handlers(application):
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("pay", pay))
    application.add_handler(CommandHandler("add_bonus", add_bonus))
    application.add_handler(CallbackQueryHandler(handle_withdrawal_action, pattern="^withdraw_"))