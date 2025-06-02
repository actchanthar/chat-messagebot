from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
import asyncio
from config import GROUP_CHAT_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory cache for channels, phone bill reward, and message rate
CHANNELS_CACHE = None
PHONE_BILL_REWARD_CACHE = None
MESSAGE_RATE_CACHE = None
CACHE_REFRESH_INTERVAL = 300  # Refresh cache every 5 minutes (in seconds)

async def refresh_channels_cache():
    global CHANNELS_CACHE
    CHANNELS_CACHE = await db.get_channels()
    logger.info("Refreshed channels cache")

async def refresh_settings_cache():
    global PHONE_BILL_REWARD_CACHE, MESSAGE_RATE_CACHE
    PHONE_BILL_REWARD_CACHE = await db.get_phone_bill_reward()
    MESSAGE_RATE_CACHE = await db.get_message_rate()
    logger.info("Refreshed settings cache")

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int) -> tuple[bool, list]:
    global CHANNELS_CACHE

    # Refresh channels cache if empty or outdated
    if CHANNELS_CACHE is None:
        await refresh_channels_cache()

    channels = CHANNELS_CACHE
    if not channels:
        logger.info("No channels found for subscription check")
        return True, []  # No channels to check

    # Check subscription status for all channels concurrently
    async def check_channel(channel):
        try:
            member = await context.bot.get_chat_member(channel["channel_id"], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                logger.info(f"User {user_id} not subscribed to channel {channel['channel_id']}")
                return channel
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id} in channel {channel['channel_id']}: {e}")
            return channel  # Treat as not subscribed if error occurs
        return None

    # Run checks concurrently
    results = await asyncio.gather(*[check_channel(channel) for channel in channels])
    not_subscribed_channels = [result for result in results if result is not None]

    return len(not_subscribed_channels) == 0, not_subscribed_channels

async def get_top_users(target_group: str, limit: int = 10):
    # Query only the top 10 users directly from the database, sorted by group_messages
    pipeline = [
        {"$match": {f"group_messages.{target_group}": {"$exists": True, "$gt": 0}}},
        {"$sort": {f"group_messages.{target_group}": -1}},
        {"$limit": limit}
    ]
    top_users = await db.get_users_with_pipeline(pipeline)
    return top_users

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Start command initiated by user {user_id} in chat {chat_id}")

    # Check if user has already passed subscription check
    user = await db.get_user(user_id)
    if user and user.get("subscription_verified", False):
        logger.info(f"User {user_id} already passed subscription check")
        subscribed = True
        not_subscribed_channels = []
    else:
        # Check force subscription
        subscribed, not_subscribed_channels = await check_subscription(context, int(user_id), chat_id)
        if subscribed and user:
            await db.update_user(user_id, {"subscription_verified": True})
            logger.info(f"Marked user {user_id} as subscription verified")

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

    # Create user if not exists
    if not user:
        user = await db.create_user(user_id, {
            "first_name": update.effective_user.first_name,
            "last_name": update.effective_user.last_name,
            "subscription_verified": subscribed
        })
        if not user:
            logger.error(f"Failed to create user {user_id}")
            await update.message.reply_text("Error creating user. Please try again later.")
            return
        logger.info(f"Created new user {user_id} during start command")

    # Base welcome message
    welcome_message = (
        "စာပို့ရင်း ငွေရှာမယ်:\n"
        f"Welcome to the Chat Bot, {update.effective_user.first_name}! 🎉\n\n"
        "Earn money by sending messages in the group!\n"
        "အုပ်စုတွင် စာပို့ခြင်းဖြင့် ငွေရှာပါ။\n\n"
        "Dev: @When_the_night_falls_my_soul_se\n"
        "Updates Channel: https://t.me/ITAnimeAI\n\n"
    )

    # Refresh settings cache if empty
    global PHONE_BILL_REWARD_CACHE, MESSAGE_RATE_CACHE
    if PHONE_BILL_REWARD_CACHE is None or MESSAGE_RATE_CACHE is None:
        await refresh_settings_cache()

    # Fetch top users directly from the database
    target_group = "-1002061898677"
    top_users = await get_top_users(target_group, limit=10)

    if top_users and top_users[0].get("group_messages", {}).get(target_group, 0) > 0:
        top_message = (
            "🏆 Top Users (by messages):\n\n"
            f"(၇ ရက်တစ်ခါ Top 1-3 ရတဲ့လူကို {PHONE_BILL_REWARD_CACHE} မဲဖောက်ပေးပါတယ်):\n\n"
        )
        for i, user in enumerate(top_users, 1):
            group_messages = user.get("group_messages", {}).get(target_group, 0)
            balance = user.get("balance", 0)
            balance_rounded = int(balance)
            if i <= 3:
                top_message += f"{i}. <b>{user.get('first_name', 'Unknown')} {user.get('last_name', '')}</b> - {group_messages} msg, {balance_rounded} kyat\n"
            else:
                top_message += f"{i}. {user.get('first_name', 'Unknown')} {user.get('last_name', '')} - {group_messages} msg, {balance_rounded} kyat\n"
        welcome_message += top_message

    welcome_message += (
        f"\nCurrent earning rate: {MESSAGE_RATE_CACHE} messages = 1 kyat\n"
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

# Schedule periodic cache refresh
async def on_startup(application: Application):
    while True:
        await refresh_channels_cache()
        await refresh_settings_cache()
        await asyncio.sleep(CACHE_REFRESH_INTERVAL)