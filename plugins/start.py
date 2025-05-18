from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest
from config import BOT_TOKEN, REQUIRED_CHANNELS, ADMIN_IDS, LOG_CHANNEL_ID
from database.database import db
import logging
import datetime

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
        logger.info(f"User {user_id} subscription check for {channel_id}: status={member.status}, is_member={is_member}")
        return is_member
    except Exception as e:
        logger.error(f"Error checking subscription for {user_id} in {channel_id}: {str(e)}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Start by {user_id} in {chat_id}, args: {context.args}")

    referrer_id = None
    if context.args and context.args[0].startswith("referrer="):
        referrer_id = context.args[0].split("referrer=")[1]

    user = db.get_user(user_id)
    if not user:
        user = db.create_user(user_id, update.effective_user.full_name, referrer_id)
        logger.info(f"Created user {user_id} with referrer {referrer_id}")

    if user.get("referrer_id"):
        referrer_id = user["referrer_id"]
        success = db.increment_invited_users(referrer_id)
        if success and referrer_id != user_id:
            referrer = db.get_user(referrer_id)
            if referrer:
                bot_username = (await context.bot.get_me()).username
                new_invite_link = f"https://t.me/{bot_username}?start=referrer={referrer_id}"
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 New user joined via your referral! Invites: {referrer.get('invited_users', 0) + 1}\nLink: {new_invite_link}",
                        disable_web_page_preview=True
                    )
                except Exception as e:
                    logger.error(f"Failed to notify referrer {referrer_id}: {e}")

    required_channels = db.get_required_channels() or REQUIRED_CHANNELS
    db.set_required_channels(required_channels)
    logger.info(f"Required channels: {required_channels}")

    if user_id not in ADMIN_IDS and required_channels:
        not_subscribed_channels = []
        for channel_id in required_channels:
            if not await check_subscription(context, user_id, channel_id):
                not_subscribed_channels.append(channel_id)

        if not_subscribed_channels:
            keyboard = []
            for channel_id in not_subscribed_channels:
                try:
                    chat = await context.bot.get_chat(channel_id)
                    invite_link = await context.bot.export_chat_invite_link(channel_id)
                    keyboard.append([InlineKeyboardButton(f"Join {chat.title}", url=invite_link)])
                except Exception as e:
                    logger.error(f"Failed to get invite link for {channel_id}: {e}")
                    channel_link = f"https://t.me/{channel_id.replace('-100', '')}"
                    keyboard.append([InlineKeyboardButton(f"Join Channel {channel_id}", url=channel_link)])

            await update.message.reply_text(
                "🎉 Welcome! Join these channels to use the bot:\n\nAfter joining, use /start again.\nInvites counted, but subscribe to withdraw.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                disable_web_page_preview=True
            )
            return

    welcome_message = (
        "စာပို့ရင်း ငွေရှာမယ်:\n"
        f"Welcome, {update.effective_user.full_name}! 🎉\n\n"
        "Earn money by sending messages in the group!\n"
        "အုပ်စုတွင် စာပို့ခြင်းဖြင့် ငွေရှာပါ။\n\n"
    )

    users = db.get_all_users()
    if users:
        target_group = "-1002061898677"
        sorted_users = sorted(
            users,
            key=lambda x: x.get("group_messages", {}).get(target_group, 0),
            reverse=True
        )[:10]
        if sorted_users and sorted_users[0].get("group_messages", {}).get(target_group, 0) > 0:
            phone_bill_reward = db.get_phone_bill_reward()
            top_message = (
                "🏆 Top Users:\n\n"
                f"(၇ ရက်တစ်ခါ Top 1-3 ရတဲ့လူကို {phone_bill_reward} မဲဖောက်ပေးပါတယ်):\n\n"
            )
            for i, user in enumerate(sorted_users, 1):
                group_messages = user.get("group_messages", {}).get(target_group, 0)
                balance = user.get("balance", 0)
                top_message += f"{i}. {'<b>' if i <= 3 else ''}{user['name']}{'</b>' if i <= 3 else ''} - {group_messages} messages, {balance} kyat\n"
            welcome_message += top_message

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
    try:
        await update.message.reply_text(welcome_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        logger.info(f"Sent welcome to {user_id} in {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send welcome to {user_id}: {e}")
        await context.bot.send_message(chat_id=chat_id, text=welcome_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def start_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(query.from_user.id)
    chat_id = query.message.chat.id
    logger.info(f"Withdraw button by {user_id} in {chat_id}")

    await query.answer()
    if query.message.chat.type != "private":
        await query.message.reply_text("Please use /withdraw in private chat.")
        return

    from plugins.withdrawal import withdraw  # Import dynamically
    context._chat_id = chat_id
    context._user_id = user_id
    await withdraw(query.message, context)

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Only admins can add channels.")
        return
    if not context.args:
        await update.message.reply_text("Provide channel ID or @username (e.g., /addchnl -100123456789).")
        return

    channel = context.args[0]
    if channel.startswith('@'):
        try:
            chat = await context.bot.get_chat(channel)
            channel = str(chat.id)
        except Exception as e:
            logger.error(f"Failed to resolve {channel}: {e}")
            await update.message.reply_text("Invalid channel or bot lacks access.")
            return
    elif not channel.startswith('-'):
        channel = f"-100{channel}"

    required_channels = db.get_required_channels()
    if channel in required_channels:
        await update.message.reply_text(f"Channel {channel} already in list.")
        return

    required_channels.append(channel)
    db.set_required_channels(required_channels)
    await update.message.reply_text(f"Added {channel} to force-sub list.")
    logger.info(f"Added {channel} by {user_id}")

async def del_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Only admins can remove channels.")
        return
    if not context.args:
        await update.message.reply_text("Provide channel ID or @username.")
        return

    channel = context.args[0]
    if channel.startswith('@'):
        try:
            chat = await context.bot.get_chat(channel)
            channel = str(chat.id)
        except Exception as e:
            logger.error(f"Failed to resolve {channel}: {e}")
            await update.message.reply_text("Invalid channel or bot lacks access.")
            return
    elif not channel.startswith('-'):
        channel = f"-100{channel}"

    required_channels = db.get_required_channels()
    if channel not in required_channels:
        await update.message.reply_text(f"Channel {channel} not in list.")
        return

    required_channels.remove(channel)
    db.set_required_channels(required_channels)
    await update.message.reply_text(f"Removed {channel} from force-sub list.")
    logger.info(f"Removed {channel} by {user_id}")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Only admins can view channels.")
        return

    required_channels = db.get_required_channels()
    if not required_channels:
        await update.message.reply_text("No force-sub channels.")
        return

    channels_text = "\n".join([f"- {ch}" for ch in required_channels])
    await update.message.reply_text(f"Force-sub channels:\n{channels_text}")
    logger.info(f"Listed {len(required_channels)} channels for {user_id}")

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(query.from_user.id)
    chat_id = query.message.chat.id
    logger.info(f"Check balance by {user_id} in {chat_id}")

    user = db.get_user(user_id)
    if not user:
        await query.message.reply_text("Run /start to register.")
        return

    balance = user.get("balance", 0)
    message = f"Your balance is {balance} kyat.\nသင့်လက်ကျန်ငွေမှာ {balance} kyat ဖြစ်ပါသည်。"
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
    try:
        await query.answer()
        await query.message.edit_text(text=message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        logger.info(f"Updated balance for {user_id} in {chat_id}")
    except Exception as e:
        logger.error(f"Failed to update balance for {user_id}: {e}")
        await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addchnl", add_channel))
    application.add_handler(CommandHandler("delchnl", del_channel))
    application.add_handler(CommandHandler("listchnl", list_channels))
    application.add_handler(CallbackQueryHandler(check_balance, pattern="^check_balance$"))
    application.add_handler(CallbackQueryHandler(start_withdraw, pattern="^start_withdraw$"))