from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define admin user IDs
ADMIN_IDS = ["5062124930"]

# Define conversation states
ENTER_MESSAGE = 0

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"Broadcast command initiated by user {user_id}")

    # Check if the user is an admin
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"User {user_id} attempted to use /broadcast but is not an admin")
        return ConversationHandler.END

    await update.message.reply_text("Please enter the message you want to broadcast to all users.")
    return ENTER_MESSAGE

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    message_text = update.message.text
    logger.info(f"Received broadcast message from user {user_id}: {message_text}")

    # Get all users from the database
    users = await db.get_all_users()
    if users is None:
        logger.error("Failed to retrieve users from database for broadcast")
        await update.message.reply_text("Error retrieving users from database. Broadcast aborted.")
        return ConversationHandler.END

    total_users = len(users)
    successful = 0
    skipped = 0
    failed = 0

    for user in users:
        user_id = user["user_id"]
        try:
            # Attempt to send the message
            sent_message = await context.bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode="Markdown"
            )
            # If message is sent successfully, try to pin it
            await context.bot.pin_chat_message(
                chat_id=user_id,
                message_id=sent_message.message_id,
                disable_notification=True
            )
            logger.info(f"Successfully broadcasted and pinned message to user {user_id}")
            successful += 1
        except Exception as e:
            if "chat not found" in str(e).lower() or "bot can't initiate conversation" in str(e).lower():
                logger.info(f"Skipped broadcasting to user {user_id}: {e}")
                skipped += 1
            else:
                logger.error(f"Failed to broadcast or pin message to user {user_id}: {e}")
                failed += 1

    # Send completion report
    report = (
        f"Broadcast completed!\n"
        f"Successfully sent to {successful} users.\n"
        f"Skipped {skipped} users (they haven't started a chat with the bot).\n"
        f"Failed to send to {failed} users."
    )
    await update.message.reply_text(report)
    logger.info(f"Broadcast report: {report}")

    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"User {user_id} canceled the broadcast")
    await update.message.reply_text("Broadcast canceled.")
    return ConversationHandler.END

def register_handlers(application: Application):
    logger.info("Registering broadcast handlers")
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast)],
        states={
            ENTER_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel_broadcast)],
    )
    application.add_handler(conv_handler)