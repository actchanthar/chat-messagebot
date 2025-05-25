from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import CURRENCY, LOG_CHANNEL_ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Top command by user {user_id} in chat {chat_id}")

    if await db.check_rate_limit(user_id):
        logger.warning(f"Rate limit for user {user_id}")
        return

    if await db.award_weekly_rewards():
        phone_bill_reward = await db.get_phone_bill_reward()
        await update.message.reply_text(
            f"Weekly rewards of 100 kyat awarded to top 3 users! (Withdrawable via {phone_bill_reward})"
        )

    users = await db.get_all_users()
    if not users:
        await update.message.reply_text("No users available yet.")
        return

    total_users = len(users)
    phone_bill_reward = await db.get_phone_bill_reward()

    # Top users by invites
    top_invites = await db.get_top_users(10, by="invites")
    top_message = (
        f"Top Users by Invites (၇ ရက်တစ်ခါ Top 1-3 ကို {phone_bill_reward} မဲဖောက်ပေးပါတယ် 🎁: 10000):\n\n"
        f"Total Users: {total_users}\n\n"
    )
    for i, user in enumerate(top_invites, 1):
        invites = user.get("invites", 0)
        balance = user.get("balance", 0)
        percentage = (invites / max(total_users, 1)) * 100
        top_message += (
            f"{i}. <b>{user['name']}</b> - {invites} invites, {percentage:.1f}% - {balance} {CURRENCY}\n" if i <= 3
            else f"{i}. {user['name']} - {invites} invites, {percentage:.1f}% - {balance} {CURRENCY}\n"
        )

    # Top users by messages
    target_group = "-1002061898677"
    top_messages = await db.get_top_users(10, by="messages")
    top_message += (
        f"\n🏆 Top Users (by messages):\n\n"
        f"(၇ ရက်တစ်ခါ Top 1-3 ကို {phone_bill_reward} မဲဖောက်ပေးပါတယ် 🎁: 10000):\n\n"
        f"Total Users: {total_users}\n\n"
    )
    for i, user in enumerate(top_messages, 1):
        messages = user.get("group_messages", {}).get(target_group, 0)
        balance = user.get("balance", 0)
        top_message += (
            f"{i}. <b>{user['name']}</b> - {messages} msg, {balance} {CURRENCY}\n" if i <= 3
            else f"{i}. {user['name']} - {messages} msg, {balance} {CURRENCY}\n"
        )

    await update.message.reply_text(top_message, parse_mode="HTML")
    logger.info(f"Sent top users list to user {user_id}")

async def rest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Rest command by user {user_id} in chat {chat_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if await db.check_rate_limit(user_id):
        logger.warning(f"Rate limit for user {user_id}")
        return

    result = await db.users.update_many({}, {"$set": {"messages": 0, "group_messages": {}}})
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

def register_handlers(application: Application):
    logger.info("Registering top and rest handlers")
    application.add_handler(CommandHandler("top", top))
    application.add_handler(CommandHandler("rest", rest))