from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import GROUP_CHAT_IDS, CHANNEL_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int) -> bool:
    channels = await db.get_channels()
    if not channels:
        return True  # No channels to check
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(channel["channel_id"], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id} in channel {channel['channel_id']}: {e}")
            return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Start command initiated by user {user_id} in chat {chat_id}")

    # Check force subscription
    if not await check_subscription(context, int(user_id), chat_id):
        channels = await db.get_channels()
        keyboard = [[InlineKeyboardButton(channel["channel_name"], url=f"https://t.me/{channel['channel_id']}")] for channel in channels]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Please join the following channels to use the bot:\n"
            "ကျေးဇူးပြု၍ အောက်ပါချန်နယ်များသို့ဝင်ရောက်ပါ။",
            reply_markup=reply_markup
        )
        logger.info(f"User {user_id} not subscribed to required channels")
        return

    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name)
        logger.info(f"Created new user {user_id} during start command")

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
            message_rate = await db.get_message_rate()
            top_message = (
                "🏆 Top Users (by messages):\n\n"
                f"(၇ ရက်တစ်ခါ Top 1-3 ရတဲ့လူကို {phone_bill_reward} မဲဖောက်ပေးပါတယ်):\n\n"
            )
            for i, user in enumerate(sorted_users, 1):
                group_messages = user.get("group_messages", {}).get(target_group, 0)
                balance = user.get("balance", 0)
                if i <= 3:
                    top_message += f"{i}. <b>{user['name']}</b> - {group_messages} msg, {balance} kyat\n"
                else:
                    top_message += f"{i}. {user['name']} - {group_messages} msg, {balance} kyat\n"
            welcome_message += top_message

    welcome_message += (
        f"\nCurrent earning rate: {message_rate} messages = 1 kyat\n"
        "Use the buttons below to check your balance, withdraw your earnings, or join our group.\n"
        "သင့်လက်ကျန်ငွေ စစ်ဆေးရန်၊ သင့်ဝင်ငွေများကို ထုတ်ယူရန် သို့မဟုတ် ကျွန်ုပ်တို့၏ အုပ်စုသို့ ဝင်ရောက်ရန် အောက်ပါခလုတ်များကို အသုံးပြုပါ။"
    )

    keyboard = [
        [
            InlineKeyboardButton("Check Balance", callback_data="balance"),
            InlineKeyboardButton("Withdraw", callback_data="withdraw")
        ],
        [InlineKeyboardButton("Join Group", url=f"https://t.me/{GROUP_CHAT_IDS[0]}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="HTML")
    logger.info(f"Sent welcome message to user {user_id} in chat {chat_id}")

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start))