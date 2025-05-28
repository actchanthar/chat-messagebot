from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import ADMIN_IDS, LOG_CHANNEL_ID, CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Add_bonus command by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized add_bonus attempt by user {user_id}")
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) < 2:
        logger.info(f"Insufficient arguments provided by user {user_id}")
        await update.message.reply_text("Usage: /Add_bonus <user_id> <amount>")
        return

    try:
        target_user_id = context.args[0]
        amount = float(context.args[1])
        if amount <= 0:
            await update.message.reply_text("Amount must be positive.")
            return

        success = await db.add_bonus(target_user_id, amount)
        if success:
            user = await db.get_user(target_user_id)
            new_balance = user.get("balance", 0) if user else 0
            new_balance_rounded = int(new_balance)  # Round to whole number
            await update.message.reply_text(
                f"Added {int(amount)} {CURRENCY} to user {target_user_id}. New balance: {new_balance_rounded} {CURRENCY}."
            )
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Admin {user_id} added {int(amount)} {CURRENCY} bonus to user {target_user_id}. New balance: {new_balance_rounded} {CURRENCY}."
            )
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"You received a bonus of {int(amount)} {CURRENCY}! Your new balance is {new_balance_rounded} {CURRENCY}."
                )
                logger.info(f"Notified user {target_user_id} of bonus: {amount} {CURRENCY}")
            except Exception as e:
                logger.error(f"Failed to notify user {target_user_id} of bonus: {e}")
                await update.message.reply_text(f"Bonus added, but failed to notify user {target_user_id}: {str(e)}")
            logger.info(f"Added {amount} {CURRENCY} bonus to user {target_user_id} by admin {user_id}")
        else:
            await update.message.reply_text("Failed to add bonus. User not found or error occurred.")
            logger.error(f"Failed to add {amount} {CURRENCY} bonus to user {target_user_id}")
    except ValueError:
        await update.message.reply_text("Invalid amount. Please provide a number.")
        logger.error(f"Invalid amount provided by user {user_id}: {context.args[1]}")
    except Exception as e:
        await update.message.reply_text("An error occurred. Please try again.")
        logger.error(f"Error in add_bonus for user {target_user_id}: {e}")

def register_handlers(application: Application):
    logger.info("Registering add_bonus handler")
    application.add_handler(CommandHandler("Add_bonus", add_bonus))