from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)
from config import ADMIN_IDS, CURRENCY
from database.database import db
import logging
from datetime import datetime, timezone

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define conversation states
STEP_USER_ID, STEP_AMOUNT = range(2)

# Start the /add_bonus command
async def add_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Add bonus function called by user {user_id} in chat {chat_id}")

    # Restrict to admins only
    if user_id not in ADMIN_IDS:
        logger.info(f"User {user_id} attempted to use /add_bonus but is not an admin")
        await update.message.reply_text("This command is restricted to admins only.")
        return ConversationHandler.END

    await update.message.reply_text("Please enter the User ID of the user to add a bonus to.")
    return STEP_USER_ID

# Handle the user ID input
async def handle_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    target_user_id = update.message.text.strip()
    logger.info(f"Admin {user_id} provided target User ID: {target_user_id}")

    # Validate the target user exists
    target_user = await db.get_user(target_user_id)
    if not target_user:
        logger.error(f"Target user {target_user_id} not found in database")
        await update.message.reply_text("User not found. Please try again with a valid User ID.")
        return STEP_USER_ID

    context.user_data["target_user_id"] = target_user_id
    context.user_data["target_user"] = target_user
    await update.message.reply_text("Please enter the bonus amount to add (e.g., 500).")
    return STEP_AMOUNT

# Handle the bonus amount input
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_id = str(update.effective_user.id)
    target_user_id = context.user_data.get("target_user_id")
    target_user = context.user_data.get("target_user")
    message = update.message
    logger.info(f"Admin {admin_id} provided bonus amount: {message.text}")

    try:
        amount = int(message.text.strip())
        if amount <= 0:
            await message.reply_text("Please enter a positive amount.")
            return STEP_AMOUNT

        # Update the user's balance
        current_balance = target_user.get("balance", 0)
        new_balance = current_balance + amount
        result = await db.update_user(target_user_id, {"balance": new_balance})
        logger.info(f"db.update_user returned: {result} for user {target_user_id} with new balance {new_balance}")

        # Check if the update was successful
        success = False
        if isinstance(result, bool):
            success = result
        elif hasattr(result, 'modified_count'):
            success = result.modified_count > 0
        else:
            logger.error(f"Unexpected db.update_user result type: {type(result)} for user {target_user_id}")

        if success:
            logger.info(f"Bonus of {amount} {CURRENCY} added to user {target_user_id}. New balance: {new_balance}")
            
            # Notify the admin
            await message.reply_text(
                f"Bonus of {amount} {CURRENCY} added to User ID {target_user_id}. Their new balance is {new_balance} {CURRENCY}."
            )

            # Notify the user
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"You have received a bonus of {amount} {CURRENCY}! Your new balance is {new_balance} {CURRENCY}.\n"
                         f"သင်သည် {amount} {CURRENCY} ဘောနပ်စ်ရရှိခဲ့ပါသည်။ သင့်လက်ကျန်ငွေ အသစ်မှာ {new_balance} {CURRENCY} ဖြစ်ပါသည်။"
                )
                logger.info(f"Notified user {target_user_id} of bonus addition")
            except Exception as e:
                logger.error(f"Failed to notify user {target_user_id} of bonus addition: {e}")
                await message.reply_text(f"Bonus added, but failed to notify the user: {str(e)}")

        else:
            logger.error(f"Failed to update balance for user {target_user_id}. Result: {result}")
            await message.reply_text("Error adding bonus. Please try again.")

    except ValueError:
        await message.reply_text("Please enter a valid number (e.g., 500).")
        return STEP_AMOUNT

    context.user_data.clear()
    return ConversationHandler.END

# Cancel the add bonus process
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"User {user_id} canceled the add bonus process")
    await update.message.reply_text("Add bonus canceled.")
    context.user_data.clear()
    return ConversationHandler.END

def register_handlers(application: Application):
    logger.info("Registering add_bonus handlers")
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("add_bonus", add_bonus),
        ],
        states={
            STEP_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_id)],
            STEP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex("^(Cancel|cancel)$"), cancel),
        ],
    )

    application.add_handler(conv_handler)