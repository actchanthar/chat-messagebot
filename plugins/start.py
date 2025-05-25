from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from database.database import db
import logging
from config import BOT_USERNAME, FORCE_SUB_CHANNELS, GROUP_CHAT_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    args = context.args
    invited_by = args[0] if args else None
    logger.info(f"Start command by user {user_id} in chat {chat_id}, invited_by: {invited_by}")

    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name, invited_by)
        if not user:
            logger.error(f"Failed to create user {user_id}")
            await update.message.reply_text("Error creating user. Please try again or contact support.")
            return
        logger.info(f"Created new user {user_id}")

    # Check subscription to all required channels
    all_subscribed = True
    failed_channels = []
    for channel_id in FORCE_SUB_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel_id, user_id)
            if member.status in ["member", "administrator", "creator"]:
                await db.update_subscription(user_id, channel_id)
                logger.info(f"User {user_id} subscribed to {channel_id}")
            else:
                all_subscribed = False
                failed_channels.append(channel_id)
                logger.info(f"User {user_id} not subscribed to {channel_id}")
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id} in channel {channel_id}: {str(e)}")
            all_subscribed = False
            failed_channels.append(channel_id)

    if not all_subscribed:
        channels = await db.get_channels()
        if not channels:
            channels = []
            for cid in FORCE_SUB_CHANNELS:
                try:
                    chat = await context.bot.get_chat(cid)
                    name = chat.title or f"Channel {cid}"
                    username = chat.username or None
                    invite_link = None
                    if not username:
                        try:
                            invite_link = await context.bot.create_chat_invite_link(cid)
                        except Exception as e:
                            logger.error(f"Failed to create invite link for {cid}: {str(e)}")
                    channels.append({"channel_id": cid, "name": name, "username": username, "invite_link": invite_link})
                except Exception as e:
                    logger.error(f"Error fetching channel {cid}: {str(e)}")
                    channels.append({"channel_id": cid, "name": f"Channel {cid}", "username": None, "invite_link": None})

        keyboard = []
        for c in channels:
            if c["username"]:
                url = f"https://t.me/{c['username'][1:]}"
            elif c["invite_link"]:
                url = c["invite_link"]
            else:
                url = f"https://t.me/c/{c['channel_id'].replace('-100', '')}"
                logger.warning(f"No username or invite link for {c['channel_id']}, using fallback URL: {url}")
            keyboard.append([InlineKeyboardButton(f"Join {c['name']}", url=url)])
        keyboard.append([InlineKeyboardButton("Check Subscription", callback_data="check_subscription")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Please join the following channels to activate your account:\n"
            "ကျေးဇူးပြု၍ အောက်ပါချန်နယ်များသို့ ဝင်ရောက်ပါ။",
            reply_markup=reply_markup
        )
        logger.info(f"Prompted user {user_id} to join channels: {failed_channels}")
        return

    # Award referral bonuses if all channels are joined
    if invited_by and user.get("invited_by") == invited_by:
        inviter = await db.get_user(invited_by)
        if inviter:
            await db.add_invite(invited_by, user_id)
            inviter_balance = inviter.get("balance", 0) + 25
            invitee_balance = user.get("balance", 0) + 50
            await db.update_user(invited_by, {"balance": inviter_balance, "invites": inviter.get("invites", 0) + 1})
            await db.update_user(user_id, {"balance": invitee_balance})
            try:
                await context.bot.send_message(
                    chat_id=invited_by,
                    text=f"You earned 25 kyat for inviting {update.effective_user.full_name}! Your new balance is {inviter_balance} kyat."
                )
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Welcome! You earned 50 kyat for joining all required channels. Your balance is {invitee_balance} kyat."
                )
            except Exception as e:
                logger.error(f"Error notifying users {invited_by}/{user_id} of referral rewards: {str(e)}")

    welcome_message = (
        f"Welcome to {BOT_USERNAME}, {update.effective_user.full_name}! 🎉\n"
        "Earn money by sending messages in the group!\n"
        "အုပ်စုတွင် စာပို့ခြင်းဖြင့် ငွေရှာပါ။\n\n"
    )

    users = await db.get_all_users()
    target_group = GROUP_CHAT_IDS[0]
    if users:
        sorted_users = sorted(
            users,
            key=lambda x: x.get("group_messages", {}).get(target_group, 0),
            reverse=True
        )[:10]
        if sorted_users and sorted_users[0].get("group_messages", {}).get(target_group, 0) > 0:
            phone_bill_reward = await db.get_phone_bill_reward()
            welcome_message += (
                f"🏆 Top Users (by messages):\n\n"
                f"(၇ ရက်တစ်ခါ Top 1-3 ကို {phone_bill_reward} မဲဖောက်ပေးပါတယ်):\n\n"
            )
            for i, user in enumerate(sorted_users, 1):
                group_messages = user.get("group_messages", {}).get(target_group, 0)
                balance = user.get("balance", 0)
                welcome_message += (
                    f"{i}. <b>{user['name']}</b> - {group_messages} msg, {balance} kyat\n" if i <= 3
                    else f"{i}. {user['name']} - {group_messages} msg, {balance} kyat\n"
                )

    welcome_message += (
        "\nUse the buttons below to check your balance, withdraw, or contact support.\n"
        "သင့်လက်ကျန်ငွေ စစ်ဆေးရန်၊ ထုတ်ယူရန် သို့မဟုတ် အုပ်စုသို့ဝင်ရောက်ရန် အောက်ပါခလုတ်များကို အသုံးပြုပါ။"
    )

    keyboard = [
        [
            InlineKeyboardButton("Check Balance", callback_data="balance"),
            InlineKeyboardButton("Withdrawal", callback_data="withdraw")
        ],
        [
            InlineKeyboardButton("Dev", url="https://t.me/When_the_night_falls_my_soul_se"),
            InlineKeyboardButton("Support Channel", url="https://t.me/ITAnimeAI")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="HTML")
    logger.info(f"Sent welcome message to user {user_id} in chat {chat_id}")

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    logger.info(f"Check subscription for user {user_id}")

    all_subscribed = True
    failed_channels = []
    for channel_id in FORCE_SUB_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel_id, user_id)
            if member.status in ["member", "administrator", "creator"]:
                await db.update_subscription(user_id, channel_id)
                logger.info(f"User {user_id} subscribed to {channel_id}")
            else:
                all_subscribed = False
                failed_channels.append(channel_id)
                logger.info(f"User {user_id} not subscribed to {channel_id}")
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id} in channel {channel_id}: {str(e)}")
            all_subscribed = False
            failed_channels.append(channel_id)

    if all_subscribed:
        await query.message.reply_text(
            "You have joined all required channels! Use /start to continue."
        )
        logger.info(f"User {user_id} subscribed to all channels")
    else:
        channels = await db.get_channels()
        if not channels:
            channels = []
            for cid in FORCE_SUB_CHANNELS:
                try:
                    chat = await context.bot.get_chat(cid)
                    name = chat.title or f"Channel {cid}"
                    username = chat.username or None
                    invite_link = None
                    if not username:
                        try:
                            invite_link = await context.bot.create_chat_invite_link(cid)
                        except Exception as e:
                            logger.error(f"Failed to create invite link for {cid}: {str(e)}")
                    channels.append({"channel_id": cid, "name": name, "username": username, "invite_link": invite_link})
                except Exception as e:
                    logger.error(f"Error fetching channel {cid}: {str(e)}")
                    channels.append({"channel_id": cid, "name": f"Channel {cid}", "username": None, "invite_link": None})

        keyboard = []
        for c in channels:
            if c["username"]:
                url = f"https://t.me/{c['username'][1:]}"
            elif c["invite_link"]:
                url = c["invite_link"]
            else:
                url = f"https://t.me/c/{c['channel_id'].replace('-100', '')}"
                logger.warning(f"No username or invite link for {c['channel_id']}, using fallback URL: {url}")
            keyboard.append([InlineKeyboardButton(f"Join {c['name']}", url=url)])
        keyboard.append([InlineKeyboardButton("Check Subscription", callback_data="check_subscription")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "Please join all required channels:\n"
            "ကျေးဇူးပြု၍ အောက်ပါချန်နယ်များသို့ ဝင်ရောက်ပါ။",
            reply_markup=reply_markup
        )
        logger.info(f"User {user_id} not subscribed to channels: {failed_channels}")

async def referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user = await db.get_user(user_id)
    if user:
        referral_link = user.get("referral_link", f"https://t.me/{BOT_USERNAME}?start={user_id}")
        await query.message.reply_text(
            f"Your referral link: {referral_link}\n"
            f"Invite friends to earn 25 kyat per user who joins all required channels!"
        )
    else:
        await query.message.reply_text("Error: User not found. Please start with /start.")

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(check_subscription, pattern="^check_subscription$"))
    application.add_handler(CallbackQueryHandler(referral_link, pattern="^referral_link$"))