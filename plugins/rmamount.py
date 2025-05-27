from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import ADMIN_IDS
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def rmamount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"rmamount command initiated by user {user_id} in chat {chat_id}")

    # Restrict command to admins
    if user_id not in ADMIN_IDS:
        logger.info(f"User {user_id} attempted rmamount but is not an admin")
        await update.message.reply_text("This command is restricted to admins.")
        return

    # Check for arguments (user_id and amount to deduct)
    args = context.args
    if len(args) != 2:
        logger.info(f"Invalid arguments provided by user {user_id}: {args}")
        await update.message.reply_text("Usage: /rmamount <user_id> <amount>")
        return

    target_user_id = args[0]
    try:
        amount_to_deduct = float(args[1])
        if amount_to_deduct <= 0:
            await update.message.reply_text("Amount must be a positive number.")
            logger.info(f"Invalid amount {amount_to_deduct} provided by user {user_id}")
            return
    except ValueError:
        logger.info(f"Invalid amount format provided by user {user_id}: {args[1]}")
        await update.message.reply_text("Invalid amount. Please provide a number.")
        return

    # Fetch target user
    user = await db.get_user(target_user_id)
    if not user:
        logger.error(f"User {target_user_id} not found")
        await update.message.reply_text(f"User {target_user_id} not found.")
        return

    # Check user's current balance
    current_balance = user.get("balance", 0)
    if current_balance < amount_to_deduct:
        logger.info(f"User {target_user_id} has insufficient balance: {current_balance} < {amount_to_deduct}")
        await update.message.reply_text(f"User {target_user_id} has only {current_balance} kyat. Cannot deduct {amount_to_deduct} kyat.")
        return

    # Deduct the amount from the user's balance
    new_balance = current_balance - amount_to_deduct
    try:
        await db.update_user(target_user_id, {"balance": new_balance})
        logger.info(f"Successfully deducted {amount_to_deduct} kyat from user {target_user_id}. New balance: {new_balance}")
        await update.message.reply_text(f"Successfully deducted {amount_to_deduct} kyat from user {target_user_id}. New balance: {new_balance} kyat.")
    except Exception as e:
        logger.error(f"Failed to deduct amount for user {target_user_id}: {e}")
        await update.message.reply_text(f"Error deducting amount for user {target_user_id}.")

def register_handlers(application: Application):
    logger.info("Registering rmamount handlers")
    application.add_handler(CommandHandler("rmamount", rmamount))