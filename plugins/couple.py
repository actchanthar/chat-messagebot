from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue
from database.database import db
import logging
import random
from datetime import datetime, timedelta
from config import GROUP_CHAT_IDS, LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def couple(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Couple command by user {user_id} in chat {chat_id}")

    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found. Please start with /start.")
        logger.info(f"User {user_id} not found for couple command")
        return

    # Check if user is already in the coupling queue
    coupling_queue = context.bot_data.get("coupling_queue", set())
    if user_id in coupling_queue:
        await update.message.reply_text("You are already in the coupling queue. Please wait for the next pairing!")
        logger.info(f"User {user_id} already in coupling queue")
        return

    # Add user to the coupling queue
    coupling_queue.add(user_id)
    context.bot_data["coupling_queue"] = coupling_queue
    await update.message.reply_text(
        "You have been added to the coupling queue! You will be paired with another user in the next 10-minute cycle."
    )
    logger.info(f"User {user_id} added to coupling queue")

    # Schedule the pairing job if not already running
    if not context.job_queue.get_jobs_by_name("pair_users"):
        context.job_queue.run_repeating(
            pair_users,
            interval=600,  # 10 minutes in seconds
            first=600,
            name="pair_users",
            context=context
        )
        logger.info("Scheduled pair_users job to run every 10 minutes")

async def pair_users(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Running pair_users job")
    coupling_queue = context.bot_data.get("coupling_queue", set())
    if len(coupling_queue) < 2:
        logger.info(f"Not enough users in coupling queue: {len(coupling_queue)}")
        return

    # Convert set to list for random sampling
    users = list(coupling_queue)
    random.shuffle(users)
    pairs = []

    # Create pairs
    for i in range(0, len(users) - 1, 2):
        pairs.append((users[i], users[i + 1]))

    # If odd number of users, one user remains unpaired
    unpaired_user = users[-1] if len(users) % 2 == 1 else None

    # Notify pairs
    for user1_id, user2_id in pairs:
        user1 = await db.get_user(user1_id)
        user2 = await db.get_user(user2_id)
        if not user1 or not user2:
            logger.error(f"User {user1_id} or {user2_id} not found during pairing")
            continue

        pair_message = (
            f"🎉 You have been paired with {user2['name']} (ID: {user2_id}) for this 10-minute cycle!\n"
            f"Start chatting in the group!"
        )
        try:
            await context.bot.send_message(
                chat_id=user1_id,
                text=pair_message
            )
            await context.bot.send_message(
                chat_id=user2_id,
                text=(
                    f"🎉 You have been paired with {user1['name']} (ID: {user1_id}) for this 10-minute cycle!\n"
                    f"Start chatting in the group!"
                )
            )
            # Announce in group
            await context.bot.send_message(
                chat_id=GROUP_CHAT_IDS[0],
                text=f"New couple formed: {user1['name']} (ID: {user1_id}) and {user2['name']} (ID: {user2_id})!"
            )
            await context.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"Couple paired: {user1['name']} (ID: {user1_id}) and {user2['name']} (ID: {user2_id})"
            )
            logger.info(f"Paired {user1_id} with {user2_id}")
        except Exception as e:
            logger.error(f"Error notifying users {user1_id} or {user2_id}: {e}")

        # Remove paired users from queue
        coupling_queue.discard(user1_id)
        coupling_queue.discard(user2_id)

    # Notify unpaired user (if any)
    if unpaired_user:
        try:
            await context.bot.send_message(
                chat_id=unpaired_user,
                text="Sorry, we couldn't find a pair for you this cycle. Please stay in the queue for the next pairing!"
            )
            logger.info(f"Unpaired user {unpaired_user} notified")
        except Exception as e:
            logger.error(f"Error notifying unpaired user {unpaired_user}: {e}")
    else:
        # Clear the queue if all users were paired
        coupling_queue.clear()

    context.bot_data["coupling_queue"] = coupling_queue
    logger.info(f"Updated coupling queue: {len(coupling_queue)} users remaining")

def register_handlers(application: Application):
    logger.info("Registering couple handler")
    application.add_handler(CommandHandler("couple", couple))