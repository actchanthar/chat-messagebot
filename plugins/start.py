from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import REQUIRED_CHANNELS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    args = context.args
    referrer_id = args[0] if args else None
    logger.info(f"Start command by user {user_id} in chat {chat_id}, referrer: {referrer_id}")

    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name, referrer_id)
        if referrer_id:
            channels = await db.get_channels()
            all_subscribed = True
            for channel in channels:
                try:
                    member = await context.bot.get_chat_member(channel["channel_id"], int(user_id))
                    if member.status not in ["member", "administrator", "creator"]:
                        all_subscribed = False
                    else:
                        await db.update_user_subscription(user_id, channel["channel_id"], True)
                except Exception as e:
                    logger.error(f"Error checking subscription for user {user_id} in channel {channel['channel_id']}: {e}")
                    all_subscribed = False
            if all_subscribed:
                await db.add_invite(referrer_id, user_id)
                await db.update_user(referrer_id, {"balance": (await db.get_user(referrer_id)).get("balance", 0) + 25})
                await db.update_user(user_id, {"balance": user.get("balance", 0) + 50})
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"Your invite link was used by {update.effective_user.full_name}! You earned 25 kyat."
                )
                await context.bot.send_message(
                    chat_id=user_id,
                    text="You joined via an invite and earned 50 kyat!"
                )

    welcome_message = (
        f"Welcome to the Chat Bot, {update.effective_user.full_name}! 🎉\n"
        "Earn money by sending messages in the group!\n"
        "အုပ်စုတွင် စာပို့ခြင်းဖြင့် ငွေရှာပါ။\n"
        "3 messages = 1 kyat\n"
    )

    users = await db.get_all_users()
    target_group = "-1002061898677"
    sorted_users = sorted(
        users,
        key=lambda x: x.get("group_messages", {}).get(target_group, 0),
        reverse=True
    )[:10]
    if sorted_users and sorted_users[0].get("group_messages", {}).get(target_group, 0) > 0:
        phone_bill_reward = await db.get_phone_bill_reward()
        top_message = (
            f"🏆 Top Users (by messages):\n\n"
            f"(၇ ရက်တစ်ခါ Top 1-3 ကို {phone_bill_reward} မဲဖောက်ပေးပါတယ် 🎁: 10000):\n\n"
        )
        for i, user in enumerate(sorted_users, 1):
            group_messages = user.get("group_messages", {}).get(target_group, 0)
            balance = user.get("balance", 0)
            top_message += f"{i}. <b>{user['name']}</b> - {group_messages} msg, {balance} kyat\n" if i <= 3 else \
                           f"{i}. {user['name']} - {group_messages} msg, {balance} kyat\n"
        welcome_message += top_message

    sorted_users_invites = sorted(users, key=lambda x: x.get("invites", 0), reverse=True)[:10]
    if sorted_users_invites and sorted_users_invites[0].get("invites", 0) > 0:
        top_invites = (
            f"\n🏆 Top Users (by invites):\n\n"
            f"(၇ ရက်တစ်ခါ Top 1-3 ကို {phone_bill_reward} မဲဖောက်ပေးပါတယ် 🎁: 10000):\n\n"
        )
        for i, user in enumerate(sorted_users_invites, 1):
            invites = user.get("invites", 0)
            balance = user.get("balance", 0)
            top_invites += f"{i}. <b>{user['name']}</b> - {invites} invites, {balance} kyat\n" if i <= 3 else \
                           f"{i}. {user['name']} - {invites} invites, {balance} kyat\n"
        welcome_message += top_invites

    welcome_message += (
        "\nUse the buttons below to check your balance, withdraw, or join our group.\n"
        f"Your referral link: t.me/{context.bot.username}?start={user_id}\n"
        "Invite users to earn 25 kyat per invite (they must join required channels for you to earn)!"
    )

    keyboard = [
        [
            InlineKeyboardButton("Check Balance", callback_data="balance"),
            InlineKeyboardButton("Withdraw", callback_data="withdraw")
        ],
        [InlineKeyboardButton("Join Group", url="https://t.me/yourgroup")]
    ]
    for channel in await db.get_channels():
        keyboard.append([InlineKeyboardButton(f"Join {channel['name']}", url=f"https://t.me/{channel['channel_id']}")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="HTML")
    logger.info(f"Sent welcome message to user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start))