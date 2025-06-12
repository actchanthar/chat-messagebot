import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
from config import CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"Transfer command by user {user_id}")

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /transfer <user_id> <amount>")
        return

    try:
        to_user_id = str(int(context.args[0]))  # Validate numeric ID
        amount = float(context.args[1])  # Allow decimal amounts
        if amount <= 0:
            await update.message.reply_text("Amount must be positive.")
            return
    except ValueError:
        await update.message.reply_text("Invalid user ID or amount. Please use a numeric ID and amount.")
        return

    try:
        user = await db.get_user(user_id)
        to_user = await db.get_user(to_user_id)

        if not user:
            await update.message.reply_text("Your account was not found.")
            return
        if not to_user:
            await update.message.reply_text("Target user not found.")
            return
        if user_id == to_user_id:
            await update.message.reply_text("You cannot transfer to yourself.")
            return
        if user["amount"] < amount:
            await update.message.reply_text("Insufficient balance.")
            return

        # Perform transfer
        await db.update_balance(user_id, -amount)
        await db.update_balance(to_user, amount)
        logger.info(f"Transferred {amount} {CURRENCY} from {user_id} to {to_user_id}")

        user_name = f"{user['first_name']} {user['last_name']}".strip() or user_id
        to_user_name = f"{to_user['first_name']} {to_user['last_name']}".strip() or to_user_id
        await update.message.reply_text(
            f"Successfully transferred {amount} {CURRENCY} to user {to_user_name}.\n"
            f"Your new balance: {user['balance'] - amount} {CURRENCY}"
        )

        # Notify recipient
        try:
            await context.bot.send_message(
                to_user_id,
                f"You received {amount} {CURRENCY} from {user_name}.\n"
                f"Your new balance: {to_user['balance'] + amount} {CURRENCY}"
            )
        except Exception as e:
            logger.warning(f"Failed to notify user {to_user_id}: {e}")

    except Exception as e:
        logger.error(f"Error in transfer for user {user_id} to {to_user_id}: {str(e)}")
        await update.message.reply_text("Failed to transfer balance. Please try again.")

def register_handlers(application: Application):
    logger.info("Registering transfer handler")
    application.add_handler(CommandHandler("transfer", transfer))