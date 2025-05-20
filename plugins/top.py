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
    logger.info(f"Top command by user {user_id} in chat {chat_id}")

    try:
        # Skip rate limit for testing; re-enable if needed
        # if await db.check_rate_limit(user_id):
        #     logger.info(f"Rate limit hit for user {user_id}")
        #     return

        # Award weekly rewards
        try:
            if await db.award_weekly_rewards():
                phone_bill_reward = await db.get_phone_bill_reward()
                await update.message.reply_text(f"Weekly rewards of 100 kyat awarded to top 3 inviters! ({phone_bill_reward})")
        except Exception as e:
            logger.error(f"Error in award_weekly_rewards: {e}")

        # Fetch users
        users = await db.get_all_users()
        if not users:
            await update.message.reply_text("No users available yet.")
            return

        total_users = len(users)
        target_group = "-1002061898677"
        phone_bill_reward = await db.get_phone_bill_reward()

        # Sort by invites
        sorted_by_invites = sorted(
            users,
            key=lambda x: x.get("invited_users", 0),
            reverse=True
        )[:10]
        invite_top_message = (
            f"Top Users by Invites (၇ ရက်တစ်ခါ Top 1-3 ကို ဖုန်းဘေ လက်ဆောင် ပေးပါတယ် 🎁: {phone_bill_reward}):\n\n"
            f"Total Users: {total_users}\n\n"
        )
        for i, user in enumerate(sorted_by_invites, 1):
            invites = user.get("invited_users", 0)
            balance = user.get("balance", 0)
            name = user.get("name", "Unknown")
            invite_top_message += f"{i}. <b>{name}</b> - {invites} invites, {balance} {CURRENCY}\n" if i <= 3 else f"{i}. {name} - {invites} invites, {balance} {CURRENCY}\n"

        # Sort by messages
        sorted_by_messages = sorted(
            users,
            key=lambda x: x.get("group_messages", {}).get(target_group, 0),
            reverse=True
        )[:10]
        message_top_message = (
            "\n🏆 Top Users (by messages):\n\n"
        )
        for i, user in enumerate(sorted_by_messages, 1):
            messages = user.get("group_messages", {}).get(target_group, 0)
            balance = user.get("balance", 0)
            name = user.get("name", "Unknown")
            message_top_message += f"{i}. <b>{name}</b> - {messages} msg, {balance} {CURRENCY}\n" if i <= 3 else f"{i}. {name} - {messages} msg, {balance} {CURRENCY}\n"

        await update.message.reply_text(invite_top_message + message_top_message, parse_mode="HTML")
        logger.info(f"Displayed leaderboard for user {user_id}")
    except Exception as e:
        logger.error(f"Error in top command for user {user_id}: {e}", exc_info=True)
        try:
            await update.message.reply_text("An error occurred while fetching the leaderboard. Try again later.")
        except Exception as reply_e:
            logger.error(f"Failed to send error message to {user_id}: {reply_e}")

async def rest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized.")
        return
    try:
        if await db.check_rate_limit(user_id):
            return
        result = await db.users.update_many({}, {"$set": {"messages": 0}})
        if result.modified_count > 0:
            await update.message.reply_text("Leaderboard reset. Messages set to 0.")
            current_top = await db.get_top_users()
            log_message = "Leaderboard reset:\n🏆 Top Users:\n"
            for i, user in enumerate(current_top, 1):
                balance = user.get("balance", 0)
                log_message += f"{i}. {user['name']}: 0 messages, {balance} {CURRENCY}\n"
            await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_message)
        else:
            await update.message.reply_text("No users found to reset.")
    except Exception as e:
        logger.error(f"Error in rest command for user {user_id}: {e}")
        await update.message.reply_text("An error occurred while resetting the leaderboard.")

def register_handlers(application: Application):
    logger.info("Registering top and rest handlers")
    application.add_handler(CommandHandler("top", top, block=False))
    application.add_handler(CommandHandler("rest", rest, block=False))