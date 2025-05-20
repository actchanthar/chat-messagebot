from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Admin user ID (replace with your admin's Telegram user ID)
ADMIN_USER_ID = "5062124930"  # Updated based on logs; change if different

async def init_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Withdrawal initiated by user {user_id} via command or button")

    user = await db.get_user(user_id)
    if not user:
        if update.callback_query:
            await update.callback_query.message.reply_text("User not found. Please start the bot with /start.")
        else:
            await update.effective_message.reply_text("User not found. Please start the bot with /start.")
        logger.warning(f"User {user_id} not found in database")
        return

    # Check if user is admin
    is_admin = user_id == ADMIN_USER_ID
    logger.info(f"User {user_id} is_admin: {is_admin}")

    # Non-admin users need at least 15 invited users and 10,000 kyat
    if not is_admin:
        invited_users = user.get("invited_users", 0)
        if invited_users < 15:
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    f"You need to invite at least 15 users to withdraw. You have invited {invited_users} users."
                )
            else:
                await update.effective_message.reply_text(
                    f"You need to invite at least 15 users to withdraw. You have invited {invited_users} users."
                )
            logger.info(f"User {user_id} has {invited_users} invites, needs 15")
            return
        if user.get("balance", 0) < 10000:
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    f"You need at least 10,000 kyat to withdraw. Your balance is {user.get('balance', 0)} kyat."
                )
            else:
                await update.effective_message.reply_text(
                    f"You need at least 10,000 kyat to withdraw. Your balance is {user.get('balance', 0)} kyat."
                )
            logger.info(f"User {user_id} balance {user.get('balance', 0)} kyat, needs 10000")
            return

    # Admin users only need 10,000 kyat
    else:
        if user.get("balance", 0) < 10000:
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    f"You need at least 10,000 kyat to withdraw. Your balance is {user.get('balance', 0)} kyat."
                )
            else:
                await update.effective_message.reply_text(
                    f"You need at least 10,000 kyat to withdraw. Your balance is {user.get('balance', 0)} kyat."
                )
            logger.info(f"Admin {user_id} balance {user.get('balance', 0)} kyat, needs 10000")
            return

    # Check withdrawal limit
    withdrawn_today = user.get("withdrawn_today", 0)
    if withdrawn_today >= 10000:
        if update.callback_query:
            await update.callback_query.message.reply_text("You have reached the daily withdrawal limit of 10,000 kyat.")
        else:
            await update.effective_message.reply_text("You have reached the daily withdrawal limit of 10,000 kyat.")
        logger.info(f"User {user_id} reached daily withdrawal limit: {withdrawn_today} kyat")
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
    if update.callback_query:
        await update.callback_query.message.reply_text(
            f"Your balance: {user.get('balance', 0)} kyat\n"
            f"Withdrawn today: {withdrawn_today} kyat\n"
            "Select withdrawal amount:",
            reply_markup=reply_markup,
        )
    else:
        await update.effective_message.reply_text(
            f"Your balance: {user.get('balance', 0)} kyat\n"
            f"Withdrawn today: {withdrawn_today} kyat\n"
            "Select withdrawal amount:",
            reply_markup=reply_markup,
        )
    logger.info(f"Displayed withdrawal options to user {user_id}")

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    callback_data = query.data
    logger.info(f"Callback query received from user {user_id}: {callback_data}")

    if callback_data == "init_withdraw":
        logger.info(f"Processing init_withdraw callback for user {user_id}")
        await init_withdraw(update, context)
        return

    if not callback_data.startswith("withdraw_"):
        logger.warning(f"Invalid callback data for user {user_id}: {callback_data}")
        await query.message.reply_text("Invalid withdrawal option. Please try again.")
        return

    try:
        amount = int(callback_data.split("_")[1])
        logger.info(f"Withdrawal callback for user {user_id}, amount {amount}")
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing withdrawal amount for user {user_id}: {callback_data}, error: {e}")
        await query.message.reply_text("Error processing withdrawal amount. Please try again.")
        return

    user = await db.get_user(user_id)
    if not user:
        await query.message.reply_text("User not found.")
        logger.warning(f"User {user_id} not found in database")
        return

    # Check balance
    current_balance = user.get("balance", 0)
    if current_balance < amount:
        await query.message.reply_text(f"Insufficient balance. Your balance is {current_balance} kyat.")
        logger.info(f"User {user_id} insufficient balance: {current_balance} kyat for {amount}")
        return

    # Check daily withdrawal limit
    withdrawn_today = user.get("withdrawn_today", 0)
    if withdrawn_today + amount > 10000:
        await query.message.reply_text(
            f"Withdrawal exceeds daily limit. You can withdraw {10000 - withdrawn_today} kyat today."
        )
        logger.info(f"User {user_id} exceeds daily limit: {withdrawn_today} + {amount} > 10000")
        return

    # Update user balance and withdrawal records
    new_balance = current_balance - amount
    try:
        await db.update_user(
            user_id,
            {
                "balance": new_balance,
                "withdrawn_today": withdrawn_today + amount,
                "last_withdrawal": query.message.date,
            },
        )
        logger.info(f"Updated user {user_id} balance to {new_balance}, withdrawn_today to {withdrawn_today + amount}")
    except Exception as e:
        logger.error(f"Error updating user {user_id} balance: {e}")
        await query.message.reply_text("Error updating balance. Please try again later.")
        return

    # Add to pending withdrawals
    try:
        await db.add_pending_withdrawal(user_id, amount, query.message.date)
        logger.info(f"Added pending withdrawal of {amount} kyat for user {user_id}")
    except Exception as e:
        logger.error(f"Error adding pending withdrawal for user {user_id}: {e}")
        await query.message.reply_text("Error processing withdrawal request. Please try again later.")
        return

    await query.message.reply_text(
        f"Withdrawal of {amount} kyat requested. Your new balance is {new_balance} kyat.\n"
        "Please wait for admin approval."
    )
    logger.info(f"Withdrawal of {amount} kyat requested by user {user_id}, new balance {new_balance}")

def register_handlers(application: Application):
    logger.info("Registering withdrawal handlers")
    application.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^(withdraw_|init_withdraw)$"))
    application.add_handler(CommandHandler("withdraw", init_withdraw))