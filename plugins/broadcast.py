from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Check if the user is an admin (you may have a list of admin IDs in config)
    admin_ids = ["YOUR_ADMIN_ID_1", "YOUR_ADMIN_ID_2"]  # Replace with actual admin IDs
    if str(user_id) not in admin_ids:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized broadcast attempt by user {user_id}")
        return

    # Check if a message is provided
    if not context.args:
        await update.message.reply_text("Please provide a message to broadcast. Usage: /broadcast <message>")
        return

    # Construct the broadcast message
    broadcast_message = " ".join(context.args)
    logger.info(f"Broadcast initiated by user {user_id}: {broadcast_message}")

    # Fetch all users from the database
    users = await db.get_all_users()
    if not users:
        await update.message.reply_text("No users found to broadcast to.")
        logger.info("No users found for broadcast")
        return

    total_users = len(users)
    successful_sends = 0
    failed_sends = 0

    # Send the message to each user
    for user in users:
        user_id = user["user_id"]
        try:
            # Skip banned users
            if user.get("banned", False):
                logger.info(f"Skipping banned user {user_id}")
                failed_sends += 1
                continue

            # Attempt to send the message
            await context.bot.send_message(
                chat_id=user_id,
                text=broadcast_message
            )
            successful_sends += 1
            logger.info(f"Broadcast message sent to user {user_id}")

        except Exception as e:
            # Log the failure reason (e.g., user blocked the bot)
            logger.error(f"Failed to send broadcast to user {user_id}: {e}")
            failed_sends += 1

    # Prepare the summary
    summary = (
        f"Broadcast completed.\n"
        f"Send users complete: {successful_sends}\n"
        f"Blocked or Fail users: {failed_sends}\n"
        f"Total Users: {total_users}"
    )
    await update.message.reply_text(summary)
    logger.info(f"Broadcast summary: {summary}")

def register_handlers(application: Application):
    logger.info("Registering broadcast handlers")
    application.add_handler(CommandHandler("broadcast", broadcast))