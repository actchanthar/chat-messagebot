from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import CURRENCY, LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Top command initiated by user {user_id} in chat {chat_id}")

    # Check and award weekly rewards
    if await db.award_weekly_rewards():
        await update.message.reply_text("Weekly rewards of 100 kyat awarded to the top 3 users!")
        logger.info(f"Weekly rewards processed for user {user_id}")

    # Fetch all users and sort by messages in -1002061898677
    users = await db.get_all_users()
    if not users:
        await update.message.reply_text("No users available yet.")
        logger.warning(f"No users found for user {user_id}")
        return

    target_group = "-1002061898677"
    sorted_users = sorted(
        users,
        key=lambda x: x.get("group_messages", {}).get(target_group, 0),
        reverse=True
    )[:10]

    if not sorted_users or sorted_users[0].get("group_messages", {}).get(target_group, 0) == 0:
        await update.message.reply_text("No messages recorded in the target group yet.")
        logger.warning(f"No messages in target group for user {user_id}")
        return

    top_message = "🏆 Top Users (by messages in group -1002061898677) (၇ ရက်တစ်ခါ Top 1-3 ရတဲ့လူကို ၁၀၀ ကျပ်ပေးပါတယ်):\n"
    for i, user in enumerate(sorted_users, 1):
        group_messages = user.get("group_messages", {}).get(target_group, 0)
        balance = user.get("balance", 0)
        if i <= 3:
            top_message += f"{i}. <b>{user['name']}</b> - {group_messages} messages, {balance} {CURRENCY}\n"
        else:
            top_message += f"{i}. {user['name']} - {group_messages} messages, {balance} {CURRENCY}\n"

    await update.message.reply_text(top_message, parse_mode="HTML")
    logger.info(f"Sent top users list to user {user_id} in chat {chat_id}")

async def rest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Rest command initiated by user {user_id} in chat {chat_id}")

    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        logger.info(f"Unauthorized rest attempt by user {user_id}")
        return

    result = await db.users.update_many({}, {"$set": {"messages": 0}})
    if result.modified_count > 0:
        await update.message.reply_text("Leaderboard has been reset. Messages set to 0, balances preserved.")
        logger.info(f"Reset messages for {result.modified_count} users by admin {user_id}")

        current_top = await db.get_top_users()
        log_message = "Leaderboard reset by admin:\n🏆 Top Users (before reset):\n"
        for i, user in enumerate(current_top, 1):
            balance = user.get("balance", 0)
            log_message += f"{i}. {user['name']}: 0 စာတို၊ {balance} {CURRENCY}\n"
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_message)
    else:
        await update.message.reply_text("No users found to reset.")
        logger.info(f"No users modified during reset by user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering top and rest handlers")
    application.add_handler(CommandHandler("top", top))
    application.add_handler(CommandHandler("rest", rest))