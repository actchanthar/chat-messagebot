from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
from plugins.checksubscription import checksubscription
import logging
import re
import asyncio

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    name = update.effective_user.full_name or "Unknown"
    username = update.effective_user.username

    if not await checksubscription(update, context):
        return

    referrer_id = None
    if context.args:
        match = re.match(r"referrer_(\d+)", context.args[0])
        if match:
            referrer_id = match.group(1)

    try:
        user = await db.get_user(user_id)
        if not user:
            max_retries = 3
            for attempt in range(max_retries):
                user = await db.create_user(user_id, name, username)
                if user:
                    break
                await asyncio.sleep(1)
                if attempt == max_retries - 1:
                    await update.message.reply_text("Failed to create user.")
                    return

            if referrer_id and referrer_id != user_id:
                referrer = await db.get_user(referrer_id)
                if referrer:
                    await db.add_invite(referrer_id, user_id)
                    await db.update_user(referrer_id, {"balance": referrer.get("balance", 0) + 25})
                    await db.update_user(user_id, {"balance": user.get("balance", 0) + 50, "referrer": referrer_id})
                    try:
                        await context.bot.send_message(referrer_id, "You earned 25 kyat for referring a new user!")
                        await context.bot.send_message(user_id, "You earned 50 kyat for joining via referral!")
                    except Exception as e:
                        logger.error(f"Error notifying referrer {referrer_id}: {e}")

        updates = {}
        if user["name"] != name:
            updates["name"] = name
        if user.get("username") != username:
            updates["username"] = username
        if updates:
            await db.update_user(user_id, updates)

        referral_link = f"https://t.me/{(await context.bot.get_me()).username}?start=referrer_{user_id}"
        keyboard = [
            [
                InlineKeyboardButton("Withdraw", callback_data="withdraw"),
                InlineKeyboardButton("Balance", callback_data="balance"),
                InlineKeyboardButton("Top", callback_data="top")
            ],
            [InlineKeyboardButton("Invite Link", url=referral_link)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = (
            f"Welcome, {name}! 😊\n"
            "မင်္ဂလာပါ! ကျွန်ုပ်တို့၏အုပ်စုတွင် ပါဝင်ပြီး စာပို့ခြင်းဖြင့် ငွေရှာနိုင်ပါသည်။\n"
            "3 messages = 1 kyat\n"
            "Invite friends to earn more! Referrer gets 25 kyat, invitee gets 50 kyat.\n"
            f"Your referral link: {referral_link}"
        )
        await update.message.reply_text(message, reply_markup=reply_markup)
    except Exception as e:
        await update.message.reply_text("An error occurred.")
        logger.error(f"Error in start for user {user_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("start", start))