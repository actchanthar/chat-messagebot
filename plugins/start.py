from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_ID = "5062124930"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Start command by user {user_id} in chat {chat_id}")

    user = await db.get_user(user_id)
    inviter_id = None

    # Handle referral
    if context.args and context.args[0].startswith("referral_"):
        inviter_id = context.args[0].replace("referral_", "")
        if not user:
            user = await db.create_user(user_id, update.effective_user.full_name)
            await db.update_user(user_id, {"inviter_id": inviter_id})
            logger.info(f"User {user_id} joined via referral from {inviter_id}")
            # Update inviter's invite count immediately
            if inviter_id and inviter_id != user_id:
                inviter = await db.get_user(inviter_id)
                if inviter:
                    inviter_invites = inviter.get("invite_count", 0) + 1
                    await db.update_user(inviter_id, {
                        "invite_count": inviter_invites,
                        "invited_users": inviter.get("invited_users", []) + [user_id]
                    })
                    try:
                        await context.bot.send_message(
                            inviter_id,
                            f"🎉 A new user has joined via your referral! You now have {inviter_invites} invites.\n"
                            f"Share this link to invite more: https://t.me/{context.bot.username}?start=referral_{inviter_id}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify inviter {inviter_id}: {e}")

    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name)

    # Skip force-sub for admin
    if user_id != ADMIN_ID:
        channels = await db.get_force_sub_channels()
        logger.info(f"Force-sub channels for user {user_id}: {channels}")
        if channels:
            all_subscribed = True
            not_subscribed = []
            channel_details = []
            for channel in channels:
                try:
                    member = await context.bot.get_chat_member(channel, int(user_id))
                    if member.status not in ["member", "administrator", "creator"]:
                        all_subscribed = False
                        not_subscribed.append(channel)
                except Exception as e:
                    logger.error(f"Error checking {channel} for user {user_id}: {e}")
                    all_subscribed = False
                    not_subscribed.append(channel)

            if not all_subscribed:
                # Build button grid with channel names
                keyboard = []
                row = []
                for channel in not_subscribed:
                    try:
                        chat = await context.bot.get_chat(channel)
                        channel_name = chat.title or channel
                        channel_url = f"https://t.me/{chat.username}" if chat.username else f"https://t.me/c/{channel[4:]}"
                        channel_details.append(f"{channel_name}: {channel_url}")
                    except Exception as e:
                        logger.error(f"Error fetching info for {channel}: {e}")
                        channel_name = channel
                        channel_url = f"https://t.me/c/{channel[4:]}"
                    row.append(InlineKeyboardButton(channel_name, url=channel_url))
                    if len(row) == 2:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)

                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "You must join all required channels to use this bot.\n"
                    "Join the channels below and try /start again.",
                    reply_markup=reply_markup
                )
                logger.info(f"User {user_id} prompted to join channels: {channel_details}")
                return
            # Reward invitee if all channels are joined (inviter already rewarded)
            elif inviter_id and inviter_id != user_id and not user.get("referral_rewarded", False):
                logger.info(f"Processing referral reward for user {user_id} invited by {inviter_id}")
                inviter = await db.get_user(inviter_id)
                if inviter:
                    inviter_balance = inviter.get("balance", 0) + 25
                    try:
                        await db.update_user(inviter_id, {"balance": inviter_balance})
                        await context.bot.send_message(
                            inviter_id,
                            f"Your invite joined all channels! +25 kyat. Total invites: {inviter.get('invite_count', 0)}"
                        )
                        await db.update_user(user_id, {
                            "balance": user.get("balance", 0) + 50,
                            "referral_rewarded": True
                        })
                        await update.message.reply_text("You joined all channels via referral! +50 kyat.")
                        logger.info(f"Reward applied: {inviter_id} +25 kyat, {user_id} +50 kyat")
                    except Exception as e:
                        logger.error(f"Error applying referral reward for {user_id} and {inviter_id}: {e}")

    referral_link = f"https://t.me/{context.bot.username}?start=referral_{user_id}"
    welcome_message = (
        f"Welcome to the Chat Bot, {update.effective_user.full_name}! 🎉\n"
        "Earn money by sending messages and inviting friends!\n"
        f"Referral Link: {referral_link}\n"
        "Invite 15 users who join our channels to withdraw!\n"
    )

    keyboard = [
        [
            InlineKeyboardButton("Check Balance", callback_data="balance"),
            InlineKeyboardButton("Withdraw", callback_data="withdraw")
        ],
        [
            InlineKeyboardButton("Dev", url="https://t.me/When_the_night_falls_my_soul_se"),
            InlineKeyboardButton("Earnings Group", url="https://t.me/stranger77777777777")
        ],
        [InlineKeyboardButton("Referral Users", callback_data="referral_users")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="HTML")
    logger.info(f"Sent welcome to user {user_id}")

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start))