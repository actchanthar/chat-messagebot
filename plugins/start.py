from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import FORCE_SUB_CHANNEL_LINKS, FORCE_SUB_CHANNEL_NAMES, BOT_TOKEN

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: str, channel_id: str) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        is_member = member.status in ["member", "administrator", "creator"]
        logger.info(f"User {user_id} subscription check for channel {channel_id}: status={member.status}, is_member={is_member}")
        await db.update_subscription_status(user_id, channel_id, is_member)
        return is_member
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id} in channel {channel_id}: {str(e)}")
        # If the bot can't access the channel, log and assume the user isn't a member
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Start command initiated by user {user_id} in chat {chat_id}")

    # Check for referral
    referrer_id = None
    if context.args and context.args[0].startswith("referrer="):
        referrer_id = context.args[0].split("referrer=")[1]

    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name, referrer_id)
        logger.info(f"Created new user {user_id} during start command with referrer {referrer_id}")

    # Check subscription to required channels
    force_sub_channels = await db.get_force_sub_channels()
    not_subscribed_channels = []
    for channel_id in force_sub_channels:
        if not await check_subscription(context, user_id, channel_id):
            not_subscribed_channels.append(channel_id)

    if not_subscribed_channels:
        # Create inline buttons for each channel
        keyboard = [
            [InlineKeyboardButton(
                f"Join {FORCE_SUB_CHANNEL_NAMES.get(channel_id, 'Channel')}",
                url=FORCE_SUB_CHANNEL_LINKS.get(channel_id, 'https://t.me/yourchannel')
            )]
            for channel_id in not_subscribed_channels
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"🎉 Welcome! To use the bot, please join the following channel(s):\n\n"
            "After joining, use /start again to proceed. 🚀",
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        return

    # If user has a referrer and has joined the channel, notify the referrer
    if user.get("referrer_id") and all(
        channel_id in user.get("subscribed_channels", []) for channel_id in force_sub_channels
    ):
        referrer_id = user["referrer_id"]
        await db.increment_invited_users(referrer_id)
        referrer = await db.get_user(referrer_id)
        if referrer:
            new_invite_link = f"https://t.me/{context.bot.username}?start=referrer={referrer_id}"
            try:
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 A new user has joined the required channel(s) via your referral! "
                         f"You now have {referrer.get('invited_users', 0)} invites.\n"
                         f"Share this link to invite more: {new_invite_link}",
                    disable_web_page_preview=True
                )
                logger.info(f"Notified referrer {referrer_id} of new invite by user {user_id}")
            except Exception as e:
                logger.error(f"Failed to notify referrer {referrer_id}: {e}")

    welcome_message = (
        "စာပို့ရင်း ငွေရှာမယ်:\n"
        f"Welcome to the Chat Bot, {update.effective_user.full_name}! 🎉\n\n"
        "Earn money by sending messages in the group!\n"
        "အုပ်စုတွင် စာပို့ခြင်းဖြင့် ငွေရှာပါ။\n\n"
    )

    # Fetch top users
    users = await db.get_all_users()
    if users:
        target_group = "-1002061898677"
        sorted_users = sorted(
            users,
            key=lambda x: x.get("group_messages", {}).get(target_group, 0),
            reverse=True
        )[:10]

        if sorted_users and sorted_users[0].get("group_messages", {}).get(target_group, 0) > 0:
            phone_bill_reward = await db.get_phone_bill_reward()
            top_message = (
                "🏆 Top Users:\n\n"
                f"(၇ ရက်တစ်ခါ Top 1-3 ရတဲ့လူကို {phone_bill_reward} မဲဖောက်ပေးပါတယ်):\n\n"
            )
            for i, user in enumerate(sorted_users, 1):
                group_messages = user.get("group_messages", {}).get(target_group, 0)
                balance = user.get("balance", 0)
                if i <= 3:
                    top_message += f"{i}. <b>{user['name']}</b> - {group_messages} messages, {balance} kyat\n"
                else:
                    top_message += f"{i}. {user['name']} - {group_messages} messages, {balance} kyat\n"
            welcome_message += top_message

    welcome_message += (
        "\nUse the buttons below to check your balance, withdraw your earnings, or join our group.\n"
        "သင့်လက်ကျန်ငွေ စစ်ဆေးရန်၊ သင့်ဝင်ငွေများကို ထုတ်ယူရန် သို့မဟုတ် ကျွန်ုပ်တို့၏ အုပ်စုသို့ ဝင်ရောက်ရန် အောက်ပါခလုတ်များကို အသုံးပြုပါ။\n\n"
        f"Your Invite Link: https://t.me/{context.bot.username}?start=referrer={user_id}"
    )

    keyboard = [
        [
            InlineKeyboardButton("Check Balance", callback_data="balance"),
            InlineKeyboardButton("Withdraw", callback_data="withdraw")
        ],
        [InlineKeyboardButton("Join Group", url="https://t.me/yourgroup")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="HTML")
    logger.info(f"Sent welcome message to user {user_id} in chat {chat_id}")

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start))