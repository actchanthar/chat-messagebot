# plugins/broadcast.py
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define admin user IDs (you can modify this list or fetch from config)
ADMIN_IDS = ["5062124930"]  # Replace with your admin user ID(s)

# Define broadcast steps
STEP_MESSAGE = 0

# Start the broadcast process
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    logger.info(f"Broadcast command initiated by user {user_id}")

    # Check if the user is an admin
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"User {user_id} attempted to use /broadcast but is not an admin")
        return ConversationHandler.END

    await update.message.reply_text("Please enter the message you want to broadcast to all users.")
    return STEP_MESSAGE

# Handle the broadcast message input
async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    message = update.message.text
    logger.info(f"Received broadcast message from user {user_id}: {message}")

    # Fetch all users from the database
    users = await db.get_all_users()
    if not users:
        await update.message.reply_text("No users found in the database to broadcast to.")
        logger.info("No users found for broadcast")
        return ConversationHandler.END

    success_count = 0
    fail_count = 0
    skip_count = 0

    # Broadcast the message to each user and pin it
    for user in users:
        user_id = user.get("_id")
        try:
            # Check if the bot can message the user by fetching chat info
            await context.bot.get_chat(chat_id=user_id)
            # Send the message
            sent_message = await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 Broadcast Message:\n{message}"
            )
            # Pin the message in the user's chat
            await context.bot.pin_chat_message(
                chat_id=user_id,
                message_id=sent_message.message_id,
                disable_notification=True
            )
            success_count += 1
            logger.info(f"Successfully broadcasted and pinned message to user {user_id}")
        except Exception as e:
            if "chat not found" in str(e) or "bot can't initiate conversation" in str(e):
                skip_count += 1
                logger.info(f"Skipped broadcasting to user {user_id}: User has not initiated conversation with the bot")
            else:
                fail_count += 1
                logger.error(f"Failed to broadcast or pin message to user {user_id}: {e}")

    # Notify the admin of the result
    await update.message.reply_text(
        f"Broadcast completed!\n"
        f"Successfully sent to {success_count} users.\n"
        f"Skipped {skip_count} users (they haven't started a chat with the bot).\n"
        f"Failed to send to {fail_count} users."
    )
    logger.info(f"Broadcast completed: {success_count} successes, {skip_count} skips, {fail_count} failures")

    return ConversationHandler.END

# Cancel the broadcast process
async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    logger.info(f"User {user_id} canceled the broadcast process")
    await update.message.reply_text("Broadcast canceled.")
    return ConversationHandler.END

# Register handlers for the application
def register_handlers(application: Application):
    logger.info("Registering broadcast handlers")
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast)],
        states={
            STEP_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel_broadcast)],
    )
    application.add_handler(conv_handler)