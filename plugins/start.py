from ferait import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN, REQUIRED_CHANNELS, ADMIN_IDS
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
        logger.info(f"User {user_id} subscription check for channel {channel_id}: status={member.status}, is_member={is_member}, user={member.user.username}")
        return is_member
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id} in channel {channel_id}: {str(e)}")
        if "user not found" in str(e).lower():
            logger.info(f"User {user_id} is likely not in channel {channel_id} or has privacy settings enabled.")
            return False
        elif "not enough rights" in str(e).lower():
            logger.error(f"Bot lacks permissions to view members in channel {channel_id}.")
            return False
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Start command initiated by user {user_id} in chat {chat_id} at {update.message.date}, args: {context.args}")

    referrer_id = None
    if context.args and context.args[0].startswith("referrer="):
        referrer_id = context.args[0].split("referrer=")[1]

    user = db.get_user(user_id)
    if not user:
        user = db.create_user(user_id, update.effective_user.full_name, referrer_id)
        logger.info(f"Created new user {user_id} with referrer {referrer_id}")

    # Handle referrer notification
    if user.get("referrer_id"):
        referrer_id = user["referrer_id"]
        success = db.increment_invited_users(referrer_id)
        logger.info(f"Increment invited_users for referrer {referrer_id}: {'Success' if success else 'Failed'}")
        referrer = db.get_user(referrer_id)
        if referrer:
            new_invite_link = f"https://t.me/{context.bot.username}?start=referrer={referrer_id}"
            try:
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=(
                        f"🎉 A new user has joined via your referral! "
                        f"You now have {referrer.get('invited_users', 0) + 1} invites.\n"
                        f"Share this link to invite more: {new_invite_link}"
                    ),
                    disable_web_page_preview=True
                )
                logger.info(f"Notified referrer {referrer_id} of new invite by user {user_id}")
            except Exception as e:
                logger.error(f"Failed to notify referrer {referrer_id}: {e}")

    # Subscription check
    required_channels = db.get_required_channels()
    if not required_channels:
        required_channels = REQUIRED_CHANNELS
        db.set_required_channels(required_channels)
    logger.info(f"Required channels: {required_channels}")

    if user_id not in ADMIN_IDS and required_channels:
        not_subscribed_channels = []
        for channel_id in required_channels:
            is_subscribed = await check_subscription(context, user_id, channel_id)
            if not is_subscribed:
                not_subscribed_channels.append(channel_id)
                logger.info(f"User {user_id} is not subscribed to channel {channel_id}")

        if not_subscribed_channels:
            keyboard = []
            for channel_id in not_subscribed_channels:
                try:
                    chat = await context.bot.get_chat(channel_id)
                    invite_link = await context.bot.export_chat_invite_link(channel_id)
                    button_text = f"Join {chat.title}"
                    keyboard.append([InlineKeyboardButton(button_text, url=invite_link)])
                    logger.info(f"Generated invite link for channel {channel_id}: {invite_link}")
                except Exception as e:
                    logger.error(f"Failed to get invite link for {channel_id}: {e}")
                    channel_link = f"https://t.me/{channel_id.replace('-100', '')}"
                    keyboard.append([InlineKeyboardButton(f"Join Channel {channel_id}", url=channel_link)])
                    logger.info(f"Using fallback link for channel {channel_id}: {channel_link}")

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"🎉 Welcome! You must join the following channel(s) to use the bot:\n\n"
                "After joining all channels, use /start again to proceed. 🚀\n"
                "Invites are counted, but you must subscribe to withdraw.\n",
                reply_markup=reply_markup,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            logger.info(f"Sent force-sub prompt to user {user_id} with {len(not_subscribed_channels)} channels")
            return

    # Build welcome message
    welcome_message = (
        "စာပို့ရင်း ငွေရှာမယ်:\n"
        f"Welcome to the Chat Bot, {update.effective_user.full_name}! 🎉\n\n"
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
                if i <= 3:
                    top_message += f"{i}. <b>{user['name']}</b> - {group_messages} messages, {balance} kyat\n"
                else:
                    top_message += f"{i}. {user['name']} - {group_messages} messages, {balance} kyat\n"
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
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        logger.info(f"Sent welcome message to user {user_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send welcome message to user {user_id}: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_message,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        logger.info(f"Sent welcome message to user {user_id} in chat {chat_id} via fallback")

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"/addchnl command initiated by user {user_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Only admins can add channels.")
        logger.info(f"User {user_id} attempted to add channel but is not an admin")
        return

    if not context.args:
        await update.message.reply_text("Please provide a channel ID or username (e.g., /addchnl -100123456789 or @channelname).")
        logger.info(f"User {user_id} provided no arguments for /addchnl")
        return

    channel = context.args[0]
    if channel.startswith('@'):
        try:
            chat = await context.bot.get_chat(channel)
            channel = str(chat.id)
        except Exception as e:
            logger.error(f"Failed to resolve channel {channel}: {e}")
            await update.message.reply_text("Invalid channel username or bot lacks access. Please use a channel ID.")
            return
    elif not channel.startswith('-'):
        channel = f"-100{channel}"

    required_channels = db.get_required_channels()
    if channel in required_channels:
        await update.message.reply_text(f"Channel {channel} is already in the force-sub list.")
        logger.info(f"Channel {channel} already exists for user {user_id}")
        return

    required_channels.append(channel)
    db.set_required_channels(required_channels)
    await update.message.reply_text(f"Added channel {channel} to force-sub list.")
    logger.info(f"Added channel {channel} to force-sub list by user {user_id}")

async def del_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"/delchnl command initiated by user {user_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Only admins can remove channels.")
        logger.info(f"User {user_id} attempted to remove channel but is not an admin")
        return

    if not context.args:
        await update.message.reply_text("Please provide a channel ID or username to remove (e.g., /delchnl -100123456789 or @channelname).")
        logger.info(f"User {user_id} provided no arguments for /delchnl")
        return

    channel = context.args[0]
    if channel.startswith('@'):
        try:
            chat = await context.bot.get_chat(channel)
            channel = str(chat.id)
        except Exception as e:
            logger.error(f"Failed to resolve channel {channel}: {e}")
            await update.message.reply_text("Invalid channel username or bot lacks access. Please use a channel ID.")
            return
    elif not channel.startswith('-'):
        channel = f"-100{channel}"

    required_channels = db.get_required_channels()
    if channel not in required_channels:
        await update.message.reply_text(f"Channel {channel} is not in the force-sub list.")
        logger.info(f"Channel {channel} not found for user {user_id}")
        return

    required_channels.remove(channel)
    db.set_required_channels(required_channels)
    await update.message.reply_text(f"Removed channel {channel} from force-sub list.")
    logger.info(f"Removed channel {channel} from force-sub list by user {user_id}")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    logger.info(f"/listchnl command initiated by user {user_id}")

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Only admins can view the channel list.")
        logger.info(f"User {user_id} attempted to list channels but is not an admin")
        return

    required_channels = db.get_required_channels()
    if not required_channels:
        await update.message.reply_text("No force-sub channels configured.")
        logger.info(f"No force-sub channels found for user {user_id}")
        return

    channels_text = "\n".join([f"- {ch}" for ch in required_channels])
    await update.message.reply_text(f"Force-sub channels:\n{channels_text}")
    logger.info(f"Listed {len(required_channels)} force-sub channels for user {user_id}")

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    logger.info(f"Check balance called by user {user_id}")

    user = db.get_user(user_id)
    if not user:
        await query.message.reply_text("User not found. Please start with /start.")
        return

    balance = user.get("balance", 0)
    await query.message.reply_text(
        f"Your current balance is {balance} kyat.\n"
        f"သင့်လက်ကျန်ငွေမှာ {balance} kyat ဖြစ်ပါသည်။"
    )

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addchnl", add_channel))
    application.add_handler(CommandHandler("delchnl", del_channel))
    application.add_handler(CommandHandler("listchnl", list_channels))
    application.add_handler(CallbackQueryHandler(check_balance, pattern="^check_balance$"))