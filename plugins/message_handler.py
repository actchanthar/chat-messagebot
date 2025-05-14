# plugins/message_handler.py
from telegram import Update
from telegram.ext import MessageHandler, CommandHandler, ContextTypes, filters
import logging
from database.database import db
from config import GROUP_CHAT_IDS  # Updated to use GROUP_CHAT_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Registered groups for message counting (moved to config.py as GROUP_CHAT_IDS)
# REGISTERED_GROUPS = ["-1002061898677", "-1002502926465"]  # Removed, use GROUP_CHAT_IDS instead

# Toggle for message counting (default to off)
COUNTING_ENABLED = False

# Command to turn on message counting
async def turn_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global COUNTING_ENABLED
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Restrict to admins
    if str(user_id) != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    COUNTING_ENABLED = True
    logger.info(f"Message counting turned ON by user {user_id} in chat {chat_id}")
    await update.message.reply_text("Message counting is now ON for all registered groups.")

# Command to turn off message counting
async def turn_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global COUNTING_ENABLED
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Restrict to admins
    if str(user_id) != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    COUNTING_ENABLED = False
    logger.info(f"Message counting turned OFF by user {user_id} in chat {chat_id}")
    await update.message.reply_text("Message counting is now OFF for all registered groups.")

# Command to add a new group
async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = str(update.effective_chat.id)

    # Allow users to add groups only in group chats
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command can only be used in a group chat.")
        return

    # Check if the group is already registered
    if chat_id in GROUP_CHAT_IDS:  # Use GROUP_CHAT_IDS from config
        await update.message.reply_text("This group is already registered for message counting.")
        return

    # Add the new group to the registered list (this would modify config.py, so we'll log it instead)
    logger.info(f"User {user_id} requested to add group {chat_id} to registered groups. Please update config.py manually.")
    await update.message.reply_text(
        f"Group {chat_id} requested for addition. Please update config.py with {chat_id} in GROUP_CHAT_IDS and redeploy."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)
    message = update.message
    logger.info(f"Processing update in chat {chat_id} (type: {update.effective_chat.type}), message: {message.text}")

    # Check if the chat is a registered group
    if chat_id not in GROUP_CHAT_IDS:  # Use GROUP_CHAT_IDS from config
        logger.info(f"Group {chat_id} not registered for message counting.")
        return

    # Check if message counting is enabled
    if not COUNTING_ENABLED:
        logger.info(f"Message counting is disabled. Skipping update in chat {chat_id}.")
        return

    # Skip counting for messages with links, stickers, or photos
    if message.entities or message.sticker or message.photo:
        logger.info(f"Spam detected from user {user_id}: {message.text if message.text else 'Media'}")
        return

    user = await db.get_user(user_id)
    if not user:
        logger.info(f"User {user_id} not found, creating new user")
        user = await db.create_user(user_id, update.effective_user.full_name)

    if user.get("banned", False):
        logger.info(f"User {user_id} is banned, skipping message counting")
        return

    # Increment message count and balance
    messages = user.get("messages", 0) + 1
    balance = user.get("balance", 0) + 1  # 1 message = 1 kyat

    # Update user in database
    success = await db.update_user(user_id, {
        "messages": messages,
        "balance": balance,
        "name": update.effective_user.full_name
    })

    if success:
        logger.info(f"Incremented messages for user {user_id}. New message count: {messages}, New balance: {balance}")

        # Notify user when balance reaches 10 kyat
        if balance >= 10 and not user.get("notified_10kyat", False):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="Congratulations! You've earned 10 ကျပ်. You can now withdraw using /withdraw. 💸"
                )
                await db.update_user(user_id, {"notified_10kyat": True})
                logger.info(f"Notified user {user_id} of 10 kyat milestone")

                # Notify in group
                username = update.effective_user.username or update.effective_user.full_name
                group_message = f"@{username} သူက 10 ကျပ်ရရှိခဲ့သည် 🎉"
                await context.bot.send_message(
                    chat_id=GROUP_CHAT_IDS[0],  # Use first group for announcement
                    text=group_message
                )
                logger.info(f"Sent 10 kyat milestone announcement to group {GROUP_CHAT_IDS[0]} for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id} or send group announcement: {e}")
    else:
        logger.error(f"Failed to update message count for user {user_id}")

def register_handlers(application):
    logger.info("Registering message handlers")
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & ~filters.COMMAND & ~filters.UpdateType.EDITED_MESSAGE,
        handle_message
    ))
    application.add_handler(CommandHandler("on", turn_on))
    application.add_handler(CommandHandler("off", turn_off))
    application.add_handler(CommandHandler("addgroup", add_group))