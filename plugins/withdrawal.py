from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Admin user ID (replace with your admin's Telegram user ID)
ADMIN_USER_ID = "YOUR_ADMIN_USER_ID"  # Update this with the actual admin user ID

async def init_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Withdrawal initiated by user {user_id}")

    user = await db.get_user(user_id)
    if not user:
        await update.effective_message.reply_text("User not found. Please start the bot with /start.")
        return

    # Check if user is admin
    is_admin = user_id == ADMIN_USER_ID

    # Non-admin users need at least 15 invited users and 10,000 kyat
    if not is_admin:
        if user.get("invited_users", 0) < 15:
            await update.effective_message.reply_text(
                f"You need to invite at least 15 users to withdraw. You have invited {user.get('invited_users', 0)} users."
            )
            return
        if user.get("balance", 0) < 10000:
            await update.effective_message.reply_text(
                f"You need at least 10,000 kyat to withdraw. Your balance is {user.get('balance', 0)} kyat."
            )
            return

    # Admin users only need 10,000 kyat
    else:
        if user.get("balance", 0) < 10000:
            await update.effective_message.reply_text(
                f"You need at least 10,000 kyat to withdraw. Your balance is {user.get('balance', 0)} kyat."
            )
            return

    # Check withdrawal limit
    withdrawn_today = user.get("withdrawn_today", 0)
    if withdrawn_today >= 10000:
        await update.effective_message.reply_text("You have reached the daily withdrawal limit of 10,000 kyat.")
        return

    keyboard = [
        [
            InlineKeyboardButton("500 kyat", callback_data="withdraw_500"),
            InlineKeyboardButton("1000 kyat", callback_data="withdraw_1000"),
        ],
        [
            InlineKeyboardButton("2500 kyat", callback_data="withdraw_2500"),
            InlineKeyboardButton("5000 kyat", callback_data="withdraw_5000"),
        ],
        [
            InlineKeyboardButton("10000 kyat", callback_data="withdraw_10000"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_message.reply_text(
        f"Your balance: {user.get('balance', 0)} kyat\n"
        f"Withdrawn today: {withdrawn_today} kyat\n"
        "Select withdrawal amount:",
        reply_markup=reply_markup,
    )

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    amount = int(query.data.split("_")[1])
    logger.info(f"Withdrawal callback for user {user_id}, amount {amount}")

    user = await db.get_user(user_id)
    if not user:
        await query.message.reply_text("User not found.")
        return

    # Check balance
    if user.get("balance", 0) < amount:
        await query.message.reply_text(f"Insufficient balance. Your balance is {user.get('balance', 0)} kyat.")
        return

    # Check daily withdrawal limit
    withdrawn_today = user.get("withdrawn_today", 0)
    if withdrawn_today + amount > 10000:
        await query.message.reply_text(
            f"Withdrawal exceeds daily limit. You can withdraw {10000 - withdrawn_today} kyat today."
        )
        return

    # Update user balance and withdrawal records
    new_balance = user.get("balance", 0) - amount
    await db.update_user(
        user_id,
        {
            "balance": new_balance,
            "withdrawn_today": withdrawn_today + amount,
            "last_withdrawal": query.message.date,
        },
    )

    # Add to pending withdrawals
    await db.add_pending_withdrawal(user_id, amount, query.message.date)

    await query.message.reply_text(
        f"Withdrawal of {amount} kyat requested. Your new balance is {new_balance} kyat.\n"
        "Please wait for admin approval."
    )
    logger.info(f"Withdrawal of {amount} kyat requested by user {user_id}, new balance {new_balance}")

def register_handlers(application: Application):
    logger.info("Registering withdrawal handlers")
    application.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^withdraw_"))
    application.add_handler(CommandHandler("withdraw", init_withdraw))