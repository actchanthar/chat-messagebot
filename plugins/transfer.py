from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, ContextTypes, filters
from database.database import db
import logging
from config import CURRENCY
from datetime import datetime

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

    # Show confirmation with unique callback data
    timestamp = int(datetime.utcnow().timestamp())
    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data=f"confirm_yes_{user_id}_{target_user_id}_{timestamp}"),
            InlineKeyboardButton("No", callback_data=f"confirm_no_{user_id}_{target_user_id}_{timestamp}")
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
    data = query.data.split("_")
    action = data[0]
    sender_id = data[1]
    target_user_id = data[2]
    timestamp = data[3]

    user_id = str(query.from_user.id)
    logger.info(f"Transfer callback received: {query.data} by user {user_id}")

    if sender_id != user_id:
        await query.answer("You are not authorized to confirm this transfer.", show_alert=True)
        logger.warning(f"Unauthorized transfer callback by user {user_id} for sender {sender_id}")
        return ConversationHandler.END

    amount = context.user_data.get("amount")
    if not amount:
        await query.edit_message_text("Transfer amount not found. Please try again.")
        logger.error(f"No amount found in context for user {user_id}")
        return ConversationHandler.END

    if action == "confirm_no":
        await query.edit_message_text("Transfer cancelled.")
        logger.info(f"User {user_id} cancelled transfer to {target_user_id}")
        return ConversationHandler.END

    if action == "confirm_yes":
        try:
            sender = await db.get_user(sender_id)
            if not sender:
                await query.edit_message_text("Sender not found. Transfer cancelled.")
                logger.error(f"Sender {sender_id} not found for transfer")
                return ConversationHandler.END

            target = await db.get_user(target_user_id)
            if not target:
                await query.edit_message_text("Target user not found. Transfer cancelled.")
                logger.error(f"Target user {target_user_id} not found for transfer")
                return ConversationHandler.END

            balance = sender.get("balance", 0)
            if balance < amount:
                await query.edit_message_text("Insufficient balance. Transfer cancelled.")
                logger.error(f"Insufficient balance for transfer by user {sender_id}, amount={amount}")
                return ConversationHandler.END

            # Perform transfer
            success = await db.transfer_balance(sender_id, target_user_id, amount)
            if success:
                new_sender_balance = balance - amount
                target_balance = target.get("balance", 0) + amount
                await query.edit_message_text(
                    f"Transferred {amount:.2f} {CURRENCY} to user {target_user_id}. Your new balance: {new_sender_balance:.2f} {CURRENCY}."
                )
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"You received {amount:.2f} {CURRENCY} from {query.from_user.full_name} (@{query.from_user.username or 'N/A'})! New balance: {target_balance:.2f} {CURRENCY}."
                )
                logger.info(f"User {sender_id} successfully transferred {amount:.2f} {CURRENCY} to {target_user_id}")
            else:
                await query.edit_message_text("Transfer failed. Check balance or contact support.")
                logger.warning(f"Transfer failed for user {sender_id} to {target_user_id}: {amount}")
        except Exception as e:
            await query.edit_message_text(f"Transfer failed due to an error: {str(e)}. Contact support.")
            logger.error(f"Error during transfer from {sender_id} to {target_user_id}: {e}")

    return ConversationHandler.END

def register_handlers(application: Application):
    logger.info("Registering transfer handlers")
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("transfer", transfer_start)],
        states={
            CONFIRM_TRANSFER: [CallbackQueryHandler(confirm_transfer, pattern="^confirm_(yes|no)_")],
        },
        fallbacks=[],
    )
    application.add_handler(conv_handler)