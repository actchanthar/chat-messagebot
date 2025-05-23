from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, ContextTypes, filters
from database.database import db
import logging
from config import CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
ENTER_DETAILS, CONFIRM_TRANSFER = range(2)

async def transfer_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"Transfer command received by user {user_id} in chat {update.effective_chat.id}")
    if update.effective_chat.type != "private":
        await update.message.reply_text("Please use /transfer in a private chat.")
        return ConversationHandler.END

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /transfer <user_id> <amount>")
        logger.info(f"Invalid transfer syntax by user {user_id}")
        return ConversationHandler.END

    target_user_id, amount = context.args
    context.user_data["target_user_id"] = target_user_id
    context.user_data["sender_id"] = user_id

    # Check if transferring to self
    if user_id == target_user_id:
        await update.message.reply_text("You cannot transfer to yourself.")
        logger.info(f"User {user_id} attempted to transfer to themselves")
        return ConversationHandler.END

    # Check if target user exists
    target_user = await db.get_user(target_user_id)
    if not target_user:
        await update.message.reply_text(f"User {target_user_id} not found.")
        logger.info(f"User {user_id} attempted to transfer to non-existent user {target_user_id}")
        return ConversationHandler.END

    # Validate amount
    try:
        amount = float(amount)
        if amount <= 0:
            await update.message.reply_text("Amount must be positive.")
            return ConversationHandler.END
        context.user_data["amount"] = amount
    except ValueError:
        await update.message.reply_text("Please provide a valid amount.")
        return ConversationHandler.END

    # Check sender's balance
    sender = await db.get_user(user_id)
    if not sender:
        await update.message.reply_text("Your account was not found. Contact support.")
        logger.error(f"User {user_id} not found for transfer")
        return ConversationHandler.END

    balance = sender.get("balance", 0)
    if balance < amount:
        await update.message.reply_text(f"Insufficient balance. Your balance is {balance:.2f} {CURRENCY}.")
        logger.info(f"User {user_id} has insufficient balance ({balance}) for transfer of {amount}")
        return ConversationHandler.END

    # Show confirmation
    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data="confirm_yes"),
            InlineKeyboardButton("No", callback_data="confirm_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Are you sure you want to transfer {amount:.2f} {CURRENCY} to user {target_user_id} (@{target_user.get('username', 'N/A')})?",
        reply_markup=reply_markup
    )
    logger.info(f"Transfer confirmation shown to user {user_id} for {amount:.2f} {CURRENCY} to {target_user_id}")
    return CONFIRM_TRANSFER

async def confirm_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = context.user_data["sender_id"]
    target_user_id = context.user_data["target_user_id"]
    amount = context.user_data["amount"]

    if query.data == "confirm_no":
        await query.message.reply_text("Transfer cancelled.")
        logger.info(f"User {user_id} cancelled transfer to {target_user_id}")
        return ConversationHandler.END

    # Handle Yes case
    try:
        success = await db.transfer_balance(user_id, target_user_id, amount)
        if success:
            await query.message.reply_text(f"Transferred {amount:.2f} {CURRENCY} to user {target_user_id}.")
            try:
                target_user = await db.get_user(target_user_id)
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"You received {amount:.2f} {CURRENCY} from {update.effective_user.full_name} (@{update.effective_user.username or 'N/A'})!"
                )
            except Exception as e:
                logger.error(f"Failed to notify user {target_user_id} of transfer: {e}")
            logger.info(f"User {user_id} successfully transferred {amount:.2f} {CURRENCY} to {target_user_id}")
        else:
            await query.message.reply_text("Transfer failed. Check balance or contact support.")
            logger.warning(f"Transfer failed for user {user_id} to {target_user_id}: {amount}")
    except Exception as e:
        await query.message.reply_text(f"Transfer failed due to an error: {str(e)}. Contact support.")
        logger.error(f"Error during transfer from {user_id} to {target_user_id}: {e}")
    
    return ConversationHandler.END

def register_handlers(application: Application):
    logger.info("Registering transfer handlers")
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("transfer", transfer_start)],
        states={
            CONFIRM_TRANSFER: [CallbackQueryHandler(confirm_transfer, pattern="^confirm_")],
        },
        fallbacks=[],
    )
    application.add_handler(conv_handler)