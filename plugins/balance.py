from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters
from telegram.error import RetryAfter
from database.database import db
import config
import logging

logger = logging.getLogger(__name__)

async def check_force_sub(bot, user_id, channel_id):
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = await db.get_user(user_id)
    if not user:
        await db.create_user(user_id, update.effective_user.first_name)
        user = await db.get_user(user_id)
    await update.message.reply_text(
        f"Hi {user['name']}!\n"
        f"Messages: {user['messages']}\n"
        f"Balance: {user['balance']} {config.CURRENCY}"
    )

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = await db.get_user(user_id)
    if not user or user['balance'] < config.WITHDRAWAL_THRESHOLD:
        await update.message.reply_text(
            f"You need at least {config.WITHDRAWAL_THRESHOLD} {config.CURRENCY} to withdraw."
        )
        return
    
    is_subscribed = await check_force_sub(context.bot, user_id, config.CHANNEL_ID)
    if not is_subscribed:
        await update.message.reply_text(
            f"Join {config.CHANNEL_USERNAME} to withdraw.\nThen try /withdraw again."
        )
        return
    
    # Store user state for withdrawal
    context.user_data["withdrawal"] = {"amount": user["balance"]}
    
    # Create payment method buttons
    keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in config.PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Select a payment method:",
        reply_markup=reply_markup
    )

async def handle_withdrawal_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if "withdrawal" not in context.user_data or "method" not in context.user_data["withdrawal"]:
        await update.message.reply_text("Please start the withdrawal process with /withdraw.")
        return
    
    method = context.user_data["withdrawal"]["method"]
    amount = context.user_data["withdrawal"]["amount"]
    user = await db.get_user(user_id)
    
    # Get message content
    text = update.message.text or ""
    photo = update.message.photo[-1] if update.message.photo else None
    
    if not text and not photo:
        await update.message.reply_text("Please send your account details or QR code.")
        return
    
    # Prepare user profile and details
    username = update.effective_user.username or update.effective_user.first_name
    profile_info = (
        f"Withdrawal Request\n"
        f"User: @{username}\n"
        f"User ID: {user_id}\n"
        f"Amount: {amount} {config.CURRENCY}\n"
        f"Method: {method}\n"
        f"Details:\n"
    )
    if text:
        profile_info += f"Text: {text}\n"
    
    # Forward to admins
    for admin_id in config.ADMIN_IDS:
        if admin_id:
            try:
                if photo:
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=photo.file_id,
                        caption=profile_info
                    )
                else:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=profile_info
                    )
            except RetryAfter as e:
                logger.warning(f"RetryAfter error for admin {admin_id}: {e}")
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    await update.message.reply_text(
        "Your withdrawal request has been sent to the admin. You'll be notified once processed."
    )
    
    # Clear user state
    context.user_data.pop("withdrawal", None)

def register_handlers(application):
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("withdraw", withdraw))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND | filters.PHOTO,
        handle_withdrawal_details
    ))