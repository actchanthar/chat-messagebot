from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import GROUP_CHAT_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int) -> tuple[bool, list]:
    channels = await db.get_channels()
    if not channels:
        logger.info("No channels found for subscription check")
        return True, []  # No channels to check

    not_subscribed_channels = []
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(channel["channel_id"], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                logger.info(f"User {user_id} not subscribed to channel {channel['channel_id']}")
                not_subscribed_channels.append(channel)
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id} in channel {channel['channel_id']}: {e}")
            not_subscribed_channels.append(channel)  # Treat as not subscribed if error occurs

    return len(not_subscribed_channels) == 0, not_subscribed_channels

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Start command initiated by user {user_id} in chat {chat_id}")

    # Check force subscription
    subscribed, not_subscribed_channels = await check_subscription(context, int(user_id), chat_id)
    if not subscribed:
        # Prepare 2-column keyboard for not subscribed channels
        keyboard = []
        for i in range(0, len(not_subscribed_channels), 2):
            row = []
            # First channel in the row
            channel_1 = not_subscribed_channels[i]
            row.append(InlineKeyboardButton(
                channel_1["channel_name"],
                url=f"https://t.me/{channel_1['channel_name'][1:]}"
            ))
            # Second channel in the row, if exists
            if i + 1 < len(not_subscribed_channels):
                channel_2 = not_subscribed_channels[i + 1]
                row.append(InlineKeyboardButton(
                    channel_2["channel_name"],
                    url=f"https://t.me/{channel_2['channel_name'][1:]}"
                ))
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Please join the following channels to use the bot:\n"
            "ကျေးဇူးပြု၍ အောက်ပါချန်နယ်များသို့ဝင်ရောက်ပါ။",
            reply_markup=reply_markup
        )
        logger.info(f"User {user_id} not subscribed to required channels: {[ch['channel_name'] for ch in not_subscribed_channels]}")
        return

    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, {
            "first_name": update.effective_user.first_name,
            "last_name": update.effective_user.last_name
        })
        if not user:
            logger.error(f"Failed to create user {user_id}")
            await update.message.reply_text("Error creating user. Please try again later.")
            return
        logger.info(f"Created new user {user_id} during start command")

    welcome_message = (
        "စာပို့ရင်း ငွေရှာမယ်:\n"
        f"Welcome to the Chat Bot, {update.effective_user.first_name}! 🎉\n\n"
        "Earn money by sending messages in the group!\n"
        "အုပ်စုတွင် စာပို့ခြင်းဖြင့် ငွေရှာပါ။\n\n"
        "Dev: @When_the_night_falls_my_soul_se\n"
        "Updates Channel: https://t.me/ITAnimeAI\n\n"
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
            message_rate = await db.get_message_rate()
            top_message = (
                "🏆 Top Users (by messages):\n\n"
                f"(၇ ရက်တစ်ခါ Top 1-3 ရတဲ့လူကို {phone_bill_reward} မဲဖောက်ပေးပါတယ်):\n\n"
            )
            for i, user in enumerate(sorted_users, 1):
                group_messages = user.get("group_messages", {}).get(target_group, 0)
                balance = user.get("balance", 0)
                balance_rounded = int(balance)
                if i <= 3:
                    top_message += f"{i}. <b>{user.get('first_name', 'Unknown')} {user.get('last_name', '')}</b> - {group_messages} msg, {balance_rounded} kyat\n"
                else:
                    top_message += f"{i}. {user.get('first_name', 'Unknown')} {user.get('last_name', '')} - {group_messages} msg, {balance_rounded} kyat\n"
            welcome_message += top_message

    welcome_message += (
        f"\nCurrent earning rate: {message_rate} messages = 1 kyat\n"
        "Use the buttons below to interact with the bot.\n"
        "အောက်ပါခလုတ်များကို အသုံးပြုပါ။"
    )

    keyboard = [
        [
            InlineKeyboardButton("Check Balance", callback_data="balance"),
            InlineKeyboardButton("Withdrawal", callback_data="withdraw")
        ],
        [
            InlineKeyboardButton("Dev", url="https://t.me/When_the_night_falls_my_soul_se"),
            InlineKeyboardButton("Updates Channel", url="https://t.me/ITAnimeAI")
        ],
        [InlineKeyboardButton("Join Earnings Group", url="https://t.me/stranger77777777777")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="HTML")
    logger.info(f"Sent welcome message to user {user_id} in chat {chat_id}")

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start))