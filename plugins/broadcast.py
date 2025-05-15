from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Broadcast command initiated by user {user_id} in chat {chat_id}")

    # Restrict to admin (user ID 5062124930)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized broadcast attempt by user {user_id}")
        return

    # Check if a message is provided
    if not context.args:
        await update.message.reply_text("Please provide a message to broadcast. Usage: /broadcast <message>")
        logger.info(f"No message provided by user {user_id}")
        return

    message = " ".join(context.args)
    logger.info(f"Broadcast initiated by user {user_id} with message: {message}")

    # Fetch all users from the database
    users = await db.get_all_users()
    if not users:
        await update.message.reply_text("No users found to broadcast to.")
        logger.warning(f"No users found for broadcast by user {user_id}")
        return

    # Broadcast to each user
    success_count = 0
    failure_count = 0
    for user in users:
        try:
            target_user_id = user["user_id"]
            # Send the message to the user's chat (user_id acts as chat_id for direct messages)
            await context.bot.send_message(chat_id=target_user_id, text=message, parse_mode="HTML")
            success_count += 1
            logger.info(f"Successfully broadcasted message to user {target_user_id}")
        except Exception as e:
            failure_count += 1
            logger.error(f"Failed to broadcast to user {target_user_id}: {str(e)}")

    # Reply to the admin with the result
    result_message = f"Broadcast completed: Sent to {success_count} users, failed for {failure_count} users."
    await update.message.reply_text(result_message)
    logger.info(f"Broadcast result for user {user_id}: {result_message}")

    # Log to admin channel
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"Broadcast by {update.effective_user.full_name}: {message}\n{result_message}"
    )

def register_handlers(application: Application):
    logger.info("Registering broadcast handlers")
    application.add_handler(CommandHandler("broadcast", broadcast))