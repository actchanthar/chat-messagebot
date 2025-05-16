# plugins/start.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import FORCE_SUB_CHANNEL_LINKS, FORCE_SUB_CHANNEL_NAMES, BOT_TOKEN

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: str, channel_id: str) -> bool:
    try:
        bot_member = await context.bot.get_chat_member(chat_id=channel_id, user_id=context.bot.id)
        bot_is_admin = bot_member.status in ["administrator", "creator"]
        if not bot_is_admin:
            logger.error(f"Bot is not an admin in channel {channel_id}. Bot status: {bot_member.status}")
            return False

        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        is_member = member.status in ["member", "administrator", "creator"]
        logger.info(f"User {user_id} subscription check for channel {channel_id}: status={member.status}, is_member={is_member}, user={member.user.username}")
        user = await db.get_user(user_id)
        if user:
            subscribed_channels = user.get("subscribed_channels", [])
            if is_member and channel_id not in subscribed_channels:
                subscribed_channels.append(channel_id)
            elif not is_member and channel_id in subscribed_channels:
                subscribed_channels.remove(channel_id)
            await db.update_user(user_id, {"subscribed_channels": subscribed_channels})
        return is_member
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id} in channel {channel_id}: {str(e)}")
        if "user not found" in str(e).lower():
            logger.info(f"User {user_id} is likely not in channel {channel_id} or has privacy settings enabled.")
        elif "not enough rights" in str(e).lower():
            logger.error(f"Bot lacks permissions to view members in channel {channel_id}.")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Start command initiated by user {user_id} in chat {chat_id} at {update.message.date}")

    referrer_id = None
    if context.args and context.args[0].startswith("referrer="):
        referrer_id = context.args[0].split("referrer=")[1]

    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name, referrer_id)
        logger.info(f"Created new user {user_id} during start command with referrer {referrer_id}")

    force_sub_channels = await db.get_force_sub_channels()
    logger.info(f"Force-sub channels from database: {force_sub_channels}")
    
    if not force_sub_channels:
        logger.info(f"No force-sub channels configured. Skipping subscription check for user {user_id}")
    else:
        not_subscribed_channels = []
        for channel_id in force_sub_channels:
            is_subscribed = await check_subscription(context, user_id, channel_id)
            if not is_subscribed:
                not_subscribed_channels.append(channel_id)
            else:
                logger.info(f"User {user_id} confirmed subscribed to channel {channel_id}")

        if not_subscribed_channels:
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

    if user.get("referrer_id"):
        referrer_id = user["referrer_id"]
        user_subscribed = not force_sub_channels or all(
            channel_id in user.get("subscribed_channels", []) for channel_id in force_sub_channels
        )
        if user_subscribed:
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
        "\nManage your earnings:\n"
        f"Your Invite Link: https://t.me/{context.bot.username}?start=referrer={user_id}\n"
        "Your Channel"
    )

    keyboard = [
        [
            InlineKeyboardButton("💰 Check Balance", callback_data="check_balance"),
            InlineKeyboardButton("💸 Withdraw", callback_data="start_withdraw")
        ],
        [
            InlineKeyboardButton("Dev", url="https://t.me/When_the_night_falls_my_soul_se"),
            InlineKeyboardButton("Earnings Group", url="https://t.me/stranger77777777777")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="HTML")
    logger.info(f"Sent welcome message to user {user_id} in chat {chat_id}")

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start))