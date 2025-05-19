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

    # Skip force-sub for admin
    if user_id != ADMIN_ID:
        channels = await db.get_force_sub_channels()
        logger.info(f"Force-sub channels for user {user_id}: {channels}")
        if channels:
            all_subscribed = True
            for channel in channels:
                try:
                    member = await context.bot.get_chat_member(channel, int(user_id))
                    if member.status not in ["member", "administrator", "creator"]:
                        all_subscribed = False
                        await update.message.reply_text(
                            f"You must join {channel} to use this bot.\n"
                            "Join all required channels and try /start again."
                        )
                        logger.info(f"User {user_id} not subscribed to {channel}")
                        return
                except Exception as e:
                    logger.error(f"Error checking {channel} for user {user_id}: {e}")
                    await update.message.reply_text(
                        f"Error checking {channel}. Ensure you join it and try /start again."
                    )
                    return
            if not all_subscribed:
                return

    # Handle referral
    if context.args and context.args[0].startswith("referral_"):
        inviter_id = context.args[0].replace("referral_", "")
        user = await db.get_user(user_id)
        if not user:
            user = await db.create_user(user_id, update.effective_user.full_name)
            await db.update_user(user_id, {"inviter_id": inviter_id})
            logger.info(f"User {user_id} joined via referral from {inviter_id}")
            # Reward inviter and invitee if all channels are joined
            if user_id != ADMIN_ID:
                inviter = await db.get_user(inviter_id)
                if inviter:
                    inviter_invites = inviter.get("invite_count", 0) + 1
                    inviter_balance = inviter.get("balance", 0) + 25
                    await db.update_user(inviter_id, {
                        "invite_count": inviter_invites,
                        "balance": inviter_balance,
                        "invited_users": inviter.get("invited_users", []) + [user_id]
                    })
                    await context.bot.send_message(
                        inviter_id,
                        f"Your invite joined all channels! +25 kyat. Total invites: {inviter_invites}."
                    )
                    await db.update_user(user_id, {"balance": user.get("balance", 0) + 50})
                    await update.message.reply_text("You joined all channels via referral! +50 kyat.")

    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name)

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