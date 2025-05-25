from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from database.database import db
import logging
from config import BOT_USERNAME, FORCE_SUB_CHANNELS

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
        all_subscribed = True
        for channel_id in FORCE_SUB_CHANNELS:
            try:
                member = await context.bot.get_chat_member(channel_id, user_id)
                if member.status in ["member", "administrator", "creator"]:
                    await db.update_subscription(user_id, channel_id)
                else:
                    all_subscribed = False
            except Exception as e:
                logger.error(f"Error checking subscription for user {user_id} in channel {channel_id}: {e}")
                all_subscribed = False
        if all_subscribed and invited_by:
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
                    logger.error(f"Error notifying users {invited_by}/{user_id} of referral rewards: {e}")
            else:
                logger.warning(f"Inviter {invited_by} not found")

        if not all_subscribed:
            channels = await db.get_channels()
            channel_text = "\n".join([f"{c['name']} ({c['channel_id']})" for c in channels])
            await update.message.reply_text(
                f"Please join the following channels to activate your account:\n{channel_text}"
            )
            return

    welcome_message = (
        f"Welcome to {BOT_USERNAME}, {update.effective_user.full_name}! 🎉\n"
        "Earn money by sending messages in the group!\n"
        "အုပ်စုတွင် စာပို့ခြင်းဖြင့် ငွေရှာပါ။\n\n"
    )

    users = await db.get_all_users()
    target_group = "-1002061898677"
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
        "\nUse the buttons below to check your balance, withdraw, or join our group.\n"
        "သင့်လက်ကျန်ငွေ စစ်ဆေးရန်၊ ထုတ်ယူရန် သို့မဟုတ် အုပ်စုသို့ဝင်ရောက်ရန် အောက်ပါခလုတ်များကို အသုံးပြုပါ။"
    )

    keyboard = [
        [
            InlineKeyboardButton("Balance", callback_data="balance"),
            InlineKeyboardButton("Withdraw", callback_data="withdraw")
        ],
        [InlineKeyboardButton("Join Group", url="https://t.me/yourgroup")],
        [InlineKeyboardButton("Referral Link", callback_data="referral_link")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="HTML")
    logger.info(f"Sent welcome message to user {user_id} in chat {chat_id}")

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
    application.add_handler(CallbackQueryHandler(referral_link, pattern="^referral_link$"))