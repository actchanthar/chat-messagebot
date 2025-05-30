from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from database.database import db
import logging
from config import GROUP_CHAT_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message_text = update.message.text if update.message.text else ""

    # Check if message is in an approved group
    approved_groups = await db.get_approved_groups()
    if chat_id not in approved_groups:
        logger.info(f"Message from user {user_id} ignored in unapproved chat {chat_id}")
        return

    user = await db.get_user(user_id)
    if not user:
        # Create user if not found
        user = await db.create_user(user_id, {
            "first_name": update.effective_user.first_name,
            "last_name": update.effective_user.last_name
        })
        if not user:
            logger.error(f"Failed to create user {user_id} in handle_message")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="An error occurred. Please try again later or contact support."
            )
            return
        logger.info(f"Created new user {user_id} during message handling")

    # Check if user is banned
    if user.get("banned", False):
        logger.info(f"Banned user {user_id} attempted to send a message in chat {chat_id}")
        return

    # Check rate limit
    rate_limited = await db.check_rate_limit(user_id, message_text)
    if rate_limited:
        logger.info(f"User {user_id} is rate limited in chat {chat_id}")
        return

    # Increment message count
    new_messages = user.get("messages", 0) + 1
    group_messages = user.get("group_messages", {})
    group_messages[chat_id] = group_messages.get(chat_id, 0) + 1

    # Update user with new message count
    await db.update_user(user_id, {
        "messages": new_messages,
        "group_messages": group_messages,
        "last_activity": update.message.date
    })

    # Check if user should earn kyat
    message_rate = await db.get_message_rate()
    if new_messages % message_rate == 0:
        current_balance = user.get("balance", 0)
        new_balance = current_balance + 1
        await db.update_user(user_id, {"balance": new_balance})
        logger.info(f"User {user_id} earned 1 kyat, new balance: {new_balance}")

        # Notify user at 10 kyat milestone
        if new_balance == 10 and not user.get("notified_10kyat", False):
            await context.bot.send_message(
                chat_id=user_id,
                text="🎉 ဂုဏ်ယူပါတယ်! သင့်လက်ကျန်ငွေ ၁၀ ကျပ် ရှိပြီဖြစ်ပါတယ်။ /withdraw ဖြင့် ငွေထုတ်နိုင်ပါပြီ။"
            )
            await db.update_user(user_id, {"notified_10kyat": True})
            logger.info(f"Notified user {user_id} of 10 kyat milestone")

def register_handlers(application: Application):
    logger.info("Registering message handlers")
    application.add_handler(
        MessageHandler(
            filters.Chat(chat_id=[int(gid) for gid in GROUP_CHAT_IDS]) & filters.TEXT & ~filters.COMMAND,
            handle_message
        ),
        group=0
    )