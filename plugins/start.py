from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
from database.database import db
from config import REQUIRED_CHANNELS, BOT_USERNAME
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Start command received from user {user_id} in chat {chat_id}")

    # Initialize user in database
    await db.add_user(
        user_id=user_id,
        name=user.first_name or "Unknown",
        username=user.username or None,
        balance=0,
        invites=0,
        message_count=0,
        banned=False
    )

    # Check if user is in a private chat
    if update.effective_chat.type != "private":
        await update.message.reply_text("Please use /start in a private chat to interact with the bot.")
        return

    # Check subscription to required channels
    joined_channels = []
    for channel_id in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user.id)
            if member.status in ["member", "administrator", "creator"]:
                joined_channels.append(channel_id)
        except Exception as e:
            logger.error(f"Error checking membership for user {user_id} in channel {channel_id}: {e}")

    if len(joined_channels) == len(REQUIRED_CHANNELS):
        # User is subscribed to all required channels
        referral_id = context.args[0] if context.args else None
        if referral_id and referral_id != user_id:
            referrer = await db.get_user(referral_id)
            if referrer:
                await db.increment_invites(referral_id)
                await db.add_balance(referral_id, 25)  # Bonus for referrer
                await db.add_balance(user_id, 50)     # Bonus for new user
                try:
                    await context.bot.send_message(
                        chat_id=referral_id,
                        text=f"A new user joined via your referral link! You earned a 25 kyat bonus."
                    )
                except Exception as e:
                    logger.error(f"Failed to notify referrer {referral_id}: {e}")

        await update.message.reply_text(
            f"Welcome, {user.first_name}! 🎉\n"
            "You have joined all required channels.\n"
            f"Use /balance to check your balance, /withdraw to cash out, and /referral_users to invite friends.\n"
            f"Bot Username: {BOT_USERNAME}"
        )
    else:
        # Prompt user to join channels
        keyboard = [
            [InlineKeyboardButton("Join Channel", url=f"https://t.me/{(await context.bot.get_chat(channel_id)).username}")]
            for channel_id in REQUIRED_CHANNELS if channel_id not in joined_channels
        ]
        keyboard.append([InlineKeyboardButton("Check Subscription ✅", callback_data="check_subscription")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Please join the following channels to start using the bot:\n"
            "အောက်ပါချန်နယ်များကိုဝင်ရောက်ပါ။",
            reply_markup=reply_markup
        )

def register_handlers(application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(start, pattern="^start$"))