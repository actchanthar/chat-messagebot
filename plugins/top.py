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

    if await db.check_rate_limit(user_id):
        logger.warning(f"Rate limit enforced for user {user_id}")
        return

    if await db.award_weekly_rewards():
        phone_bill_reward = await db.get_phone_bill_reward()
        await update.message.reply_text(f"Weekly rewards of 100 kyat awarded to top 3 users! (Withdrawable via {phone_bill_reward})")
        logger.info(f"Weekly rewards processed for user {user_id}")

    # Top users by invites
    users = await db.get_all_users()
    phone_bill_reward = await db.get_phone_bill_reward()
    top_message = f"🏆 Top Users by Invites:\n\n(၇ ရက်တစ်ခါ Top 1-3 ကို {phone_bill_reward} မဲဖောက်ပေးပါတယ် 🎁):\n\n"
    top_message += f"Total Users: {len(users)}\n\n"
    top_users = await db.get_top_users(10, sort_by="invites")
    if top_users and top_users[0].get("invites", 0) > 0:
        for i, user in enumerate(top_users, 1):
            invites = user.get("invites", 0)
            balance = user.get("balance", 0)
            top_message += f"{i}. <b>{user['name']}</b> - {invites} invites, {balance} {CURRENCY}\n" if i <= 3 else f"{i}. {user['name']} - {invites} invites, {balance} {CURRENCY}\n"

    # Top users by messages
    top_message += "\n🏆 Top Users by Messages:\n\n"
    target_group = "-1002061898677"
    top_users = await db.get_top_users(10, sort_by="messages")
    if top_users and top_users[0].get("group_messages", {}).get(target_group, 0) > 0:
        for i, user in enumerate(top_users, 1):
            messages = user.get("group_messages", {}).get(target_group, 0)
            balance = user.get("balance", 0)
            top_message += f"{i}. <b>{user['name']}</b> - {messages} msg, {balance} {CURRENCY}\n" if i <= 3 else f"{i}. {user['name']} - {messages} msg, {balance} {CURRENCY}\n"
    else:
        top_message += "No messages recorded in the target group yet.\n"

    await update.message.reply_text(top_message, parse_mode="HTML")
    logger.info(f"Sent top users list to user {user_id}")

async def rest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Rest command initiated by user {user_id} in chat {chat_id}")

    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if await db.check_rate_limit(user_id):
        logger.warning(f"Rate limit enforced for user {user_id}")
        return

    result = await db.users.update_many({}, {"$set": {"messages": 0, "group_messages": {"-1002061898677": 0}}})
    if result.modified_count > 0:
        await update.message.reply_text("Leaderboard reset. Messages set to 0, balances preserved.")
        logger.info(f"Reset messages for {result.modified_count} users by admin {user_id}")

        current_top = await db.get_top_users()
        log_message = "Leaderboard reset by admin:\n🏆 Top Users:\n"
        for i, user in enumerate(current_top, 1):
            balance = user.get("balance", 0)
            log_message += f"{i}. {user['name']}: 0 messages, {balance} {CURRENCY}\n"
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_message)
    else:
        await update.message.reply_text("No users found to reset.")
        logger.info(f"No users modified during reset by user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering top and rest handlers")
    application.add_handler(CommandHandler("top", top))
    application.add_handler(CommandHandler("rest", rest))