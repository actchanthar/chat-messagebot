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
        await update.message.reply_text(f"Weekly rewards of 100 kyat awarded to the top 3 users! (Can be withdrawn via {phone_bill_reward} မဲဖောက်ပေးပါတယ်)")
        logger.info(f"Weekly rewards processed for user {user_id}")

    users = await db.get_all_users()
    if not users:
        await update.message.reply_text("No users available yet.")
        return

    total_users = len(users)
    channels = await db.get_force_sub_channels()
    target_group = "-1002061898677"

    # Top by Invites
    sorted_by_invites = sorted(
        users,
        key=lambda x: sum(1 for ref in x.get("referrals", []) if all(
            await db.check_user_subscription(ref, ch) for ch in channels)),
        reverse=True
    )[:10]
    phone_bill_reward = await db.get_phone_bill_reward()
    top_invites_message = (
        f"Top Users by Invites ( ၇ ရက်တစ်ခါ Top 1-3 ကို ဖုန်းဘေ လက်ဆောင် ပေးပါတယ် 🎁: 10000):\n\n"
        f"Total Users: {total_users}\n\n"
    )
    for i, user in enumerate(sorted_by_invites, 1):
        invites = sum(1 for ref in user.get("referrals", []) if all(
            await db.check_user_subscription(ref, ch) for ch in channels))
        balance = user.get("balance", 0)
        top_invites_message += f"{i}. {user['name']} - {invites} invites, {balance} kyat\n"

    # Top by Messages
    sorted_by_messages = sorted(
        users,
        key=lambda x: x.get("group_messages", {}).get(target_group, 0),
        reverse=True
    )[:10]
    top_messages_message = (
        f"\n🏆 Top Users (by messages):\n"
    )
    for i, user in enumerate(sorted_by_messages, 1):
        messages = user.get("group_messages", {}).get(target_group, 0)
        balance = user.get("balance", 0)
        top_messages_message += f"{i}. {user['name']} - {messages} msg {balance}\n"

    await update.message.reply_text(top_invites_message + top_messages_message)
    logger.info(f"Sent top users list to user {user_id}")

async def rest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if await db.check_rate_limit(user_id):
        return

    result = await db.users.update_many({}, {"$set": {"messages": 0}})
    if result.modified_count > 0:
        await update.message.reply_text("Leaderboard has been reset. Messages set to 0, balances preserved.")
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