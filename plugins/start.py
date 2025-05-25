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

    # Create or fetch user
    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name, invited_by)
        if not user:
            logger.error(f"Failed to create user {user_id}")
            await update.message.reply_text("Error: Unable to create user. Contact support.")
            return
        logger.info(f"Created new user {user_id}")

    # Check subscription to required channels
    all_subscribed = True
    for channel_id in FORCE_SUB_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                all_subscribed = False
                logger.info(f"User {user_id} not subscribed to {channel_id}")
            else:
                await db.update_subscription(user_id, channel_id)
                logger.info(f"User {user_id} subscribed to {channel_id}")
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id} in channel {channel_id}: {str(e)}")
            all_subscribed = False
            await update.message.reply_text(f"Error checking channel {channel_id}. Please try again or contact support.")
            return

    if not all_subscribed:
        # Fetch channel details
        channels = []
        for cid in FORCE_SUB_CHANNELS:
            try:
                chat = await context.bot.get_chat(cid)
                name = chat.title or f"Channel {cid}"
                url = f"https://t.me/{chat.username[1:]}" if chat.username else None
                if not url:
                    try:
                        invite_link = await context.bot.create_chat_invite_link(cid)
                        url = invite_link
                    except Exception as e:
                        logger.error(f"Failed to create invite link for {cid}: {str(e)}")
                        url = f"https://t.me/c/{cid.replace('-100', '')}"
                channels.append({"channel_id": cid, "name": name, "url": url})
            except Exception as e:
                logger.error(f"Error fetching channel {cid}: {str(e)}")
                channels.append({"channel_id": cid, "name": f"Channel {cid}", "url": f"https://t.me/c/{cid.replace('-100', '')}"})

        keyboard = [[InlineKeyboardButton(f"Join {c['name']}", url=c['url'])] for c in channels]
        keyboard.append([InlineKeyboardButton("Check Subscription", callback_data="check_subscription")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Please join the following channels to activate your account:\n"
            "ကျေးဇူးပြု၍ အောက်ပါချန်နယ်များသို့ ဝင်ရောက်ပါ။",
            reply_markup=reply_markup
        )
        logger.info(f"Prompted user {user_id} to join channels")
        return

    # Handle referral bonuses
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
                    text=f"You earned 25 kyat for inviting {update.effective_user.full_name}! New balance: {inviter_balance} kyat."
                )
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Welcome! You earned 50 kyat for joining all channels. Balance: {invitee_balance} kyat."
                )
            except Exception as e:
                logger.error(f"Error notifying referral rewards for {invited_by}/{user_id}: {str(e)}")

    # Send welcome message
    welcome_message = (
        f"Welcome to {BOT_USERNAME}, {update.effective_user.full_name}! 🎉\n"
        "Earn money by sending messages in the group!\n"
        "အုပ်စုတွင် စာပို့ခြင်းဖြင့် ငွေရှာပါ။\n\n"
        "Use the buttons below to check your balance, withdraw, or contact support.\n"
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
    logger.info(f"Checking subscription for user {user_id}")

    all_subscribed = True
    for channel_id in FORCE_SUB_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                all_subscribed = False
                logger.info(f"User {user_id} not subscribed to {channel_id}")
            else:
                await db.update_subscription(user_id, channel_id)
                logger.info(f"User {user_id} subscribed to {channel_id}")
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id} in channel {channel_id}: {str(e)}")
            all_subscribed = False

    if all_subscribed:
        await query.message.reply_text("You have joined all channels! Use /start to continue.")
        logger.info(f"User {user_id} subscribed to all channels")
    else:
        channels = []
        for cid in FORCE_SUB_CHANNELS:
            try:
                chat = await context.bot.get_chat(cid)
                name = chat.title or f"Channel {cid}"
                url = f"https://t.me/{chat.username[1:]}" if chat.username else None
                if not url:
                    try:
                        invite_link = await context.bot.create_chat_invite_link(cid)
                        url = invite_link
                    except Exception as e:
                        logger.error(f"Failed to create invite link for {cid}: {str(e)}")
                        url = f"https://t.me/c/{cid.replace('-100', '')}"
                channels.append({"channel_id": cid, "name": name, "url": url})
            except Exception as e:
                logger.error(f"Error fetching channel {cid}: {str(e)}")
                channels.append({"channel_id": cid, "name": f"Channel {cid}", "url": f"https://t.me/c/{cid.replace('-100', '')}"})

        keyboard = [[InlineKeyboardButton(f"Join {c['name']}", url=c['url'])] for c in channels]
        keyboard.append([InlineKeyboardButton("Check Subscription", callback_data="check_subscription")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "Please join all required channels:\n"
            "ကျေးဇူးပြု၍ အောက်ပါချန်နယ်များသို့ ဝင်ရောက်ပါ။",
            reply_markup=reply_markup
        )
        logger.info(f"User {user_id} prompted to join channels")

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(check_subscription, pattern="^check_subscription$"))