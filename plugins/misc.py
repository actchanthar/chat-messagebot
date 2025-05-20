from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import LOG_CHANNEL_ID, CURRENCY
from datetime import datetime, timedelta

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def setinvite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /setinvite <number>")
        return

    threshold = int(context.args[0])
    if await db.set_invite_threshold(threshold):
        await update.message.reply_text(f"Invite threshold set to {threshold} for withdrawals.")
        await context.bot.send_message(LOG_CHANNEL_ID, f"Admin set invite threshold to {threshold}.")
    else:
        await update.message.reply_text("Failed to set invite threshold.")

async def add_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) < 2 or not context.args[1].isdigit():
        await update.message.reply_text("Usage: /Add_bonus <user_id> <amount>")
        return

    target_user_id, amount = context.args[0], int(context.args[1])
    if await db.add_bonus(target_user_id, amount):
        await update.message.reply_text(f"Added {amount} {CURRENCY} bonus to user {target_user_id}.")
        await context.bot.send_message(target_user_id, f"You received a {amount} {CURRENCY} bonus!")
        await context.bot.send_message(LOG_CHANNEL_ID, f"Admin added {amount} {CURRENCY} bonus to user {target_user_id}.")
    else:
        await update.message.reply_text("Failed to add bonus.")

async def setmessage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /setmessage <number>")
        return

    rate = int(context.args[0])
    if await db.set_message_rate(rate):
        await update.message.reply_text(f"Message rate set to {rate} messages per kyat.")
        await context.bot.send_message(LOG_CHANNEL_ID, f"Admin set message rate to {rate} messages per kyat.")
    else:
        await update.message.reply_text("Failed to set message rate.")

async def debug_message_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    users = await db.get_all_users()
    message = "Message Count Debug:\n"
    for user in users:
        messages = user.get("group_messages", {}).get("-1002061898677", 0)
        balance = user.get("balance", 0)
        message += f"User {user['user_id']} ({user['name']}): {messages} messages, {balance} {CURRENCY}\n"
    await update.message.reply_text(message)

async def referral_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found. Please start with /start.")
        return

    invites = user.get("invites", 0)
    referral_link = user.get("referral_link", f"https://t.me/ACTChatBot?start={user_id}")
    await update.message.reply_text(
        f"Your referral link: {referral_link}\n"
        f"You have {invites} successful invites.\n"
        f"Invite more users to earn 25 {CURRENCY} per invite!"
    )

async def couple(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if context.job_queue.get_jobs_by_name(f"couple_{user_id}"):
        await update.message.reply_text("Please wait 10 minutes before requesting another couple match.")
        return

    users = await db.get_random_users(2)
    if len(users) < 2:
        await update.message.reply_text("Not enough users for a couple match.")
        return

    user1, user2 = users
    mention1 = f"@{user1['name']}" if not user1['name'].isdigit() else user1['name']
    mention2 = f"@{user2['name']}" if not user2['name'].isdigit() else user2['name']
    await update.message.reply_text(
        f"{mention1} သူသည် {mention2} သင်နဲ့ဖူးစာဖက်ပါ ရီးစားရှာပေးတာပါ\n"
        "ပိုက်ဆံပေးစရာမလိုပါဘူး 😅 ရန်မဖြစ်ကြပါနဲ့"
    )

    context.job_queue.run_once(
        lambda ctx: None,  # Placeholder to allow re-running
        600,  # 10 minutes
        name=f"couple_{user_id}"
    )

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if len(context.args) < 2 or not context.args[1].isdigit():
        await update.message.reply_text("Usage: /transfer <user_id> <amount>")
        return

    to_user_id, amount = context.args[0], int(context.args[1])
    if await db.transfer_balance(user_id, to_user_id, amount):
        await update.message.reply_text(f"Transferred {amount} {CURRENCY} to user {to_user_id}.")
        await context.bot.send_message(to_user_id, f"You received {amount} {CURRENCY} from user {user_id}!")
    else:
        await update.message.reply_text("Transfer failed. Check user ID or balance.")

async def restwithdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id != "5062124930":
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if context.args and context.args[0].lower() == "all":
        if await db.reset_withdrawals():
            await update.message.reply_text("All withdrawal records reset.")
            await context.bot.send_message(LOG_CHANNEL_ID, "Admin reset all withdrawal records.")
    elif context.args and context.args[0].isdigit():
        target_user_id = context.args[0]
        if await db.reset_withdrawals(target_user_id):
            await update.message.reply_text(f"Withdrawal records reset for user {target_user_id}.")
            await context.bot.send_message(LOG_CHANNEL_ID, f"Admin reset withdrawal records for user {target_user_id}.")
    else:
        await update.message.reply_text("Usage: /restwithdraw <user_id> or /restwithdraw ALL")

def register_handlers(application: Application):
    logger.info("Registering misc handlers")
    application.add_handler(CommandHandler("setinvite", setinvite))
    application.add_handler(CommandHandler("Add_bonus", add_bonus))
    application.add_handler(CommandHandler("setmessage", setmessage))
    application.add_handler(CommandHandler("debug_message_count", debug_message_count))
    application.add_handler(CommandHandler("referral_users", referral_users))
    application.add_handler(CommandHandler("couple", couple))
    application.add_handler(CommandHandler("transfer", transfer))
    application.add_handler(CommandHandler("restwithdraw", restwithdraw))