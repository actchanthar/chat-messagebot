from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging
from config import BOT_USERNAME, REQUIRED_CHANNELS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    inviter_id = context.args[0] if context.args else None
    logger.info(f"Start command by user {user_id} in chat {chat_id}, inviter: {inviter_id}")

    try:
        user = await db.get_user(user_id)
        if not user:
            user = await db.create_user(user_id, update.effective_user.full_name, inviter_id)
            logger.info(f"Created new user {user_id} with inviter {inviter_id}")
            if not user:
                await update.message.reply_text("Error creating user. Try again.")
                return

        referral_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        welcome_message = (
            "စာပို့ရင်း ငွေရှာမယ်:\n"
            f"Welcome to the Chat Bot, {update.effective_user.full_name}! 🎉\n\n"
            "Earn money by sending messages in the group!\n"
            "အုပ်စုတွင် စာပို့ခြင်းဖြင့် ငွေရှာပါ။\n\n"
            f"Your referral link: {referral_link}\n"
            "Invite friends to earn 25 kyats per join, they get 50 kyats!\n"
            "Join our channels to unlock withdrawals.\n"
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
                top_message = (
                    "🏆 Top Users:\n\n"
                    f"(၇ ရက်တစ်ခါ Top 1-3 ရတဲ့လူကို {phone_bill_reward} မဲဖောက်ပေးပါတယ်):\n\n"
                )
                for i, user in enumerate(sorted_users, 1):
                    group_messages = user.get("group_messages", {}).get(target_group, 0)
                    balance = user.get("balance", 0)
                    top_message += f"{i}. <b>{user['name']}</b> - {group_messages} messages, {balance} kyat\n" if i <= 3 else f"{i}. {user['name']} - {group_messages} messages, {balance} kyat\n"
                welcome_message += top_message

        welcome_message += (
            "\nUse the buttons below to check your balance, withdraw, or join our group.\n"
            "သင့်လက်ကျန်ငွေ စစ်ဆေးရန်၊ သင့်ဝင်ငွေများကို ထုတ်ယူရန် သို့မဟုတ် ကျွန်ုပ်တို့၏ အုပ်စုသို့ ဝင်ရောက်ရန် အောက်ပါခလုတ်များကို အသုံးပြုပါ။\n"
            "Join our channels to enable withdrawals:\n" +
            "\n".join([f"https://t.me/{channel_id.replace('-100', '')}" for channel_id in REQUIRED_CHANNELS])
        )

        keyboard = [
            [
                InlineKeyboardButton("Check Balance", callback_data="balance"),
                InlineKeyboardButton("Withdraw", callback_data="withdraw")
            ],
            [InlineKeyboardButton("Join Group", url="https://t.me/yourgroup")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="HTML")
        logger.info(f"Sent welcome message to user {user_id}")
    except Exception as e:
        logger.error(f"Error in start for user {user_id}: {e}")
        try:
            await update.message.reply_text("An error occurred. Please try again or contact @actearnbot.")
        except Exception as reply_e:
            logger.error(f"Failed to send error message to {user_id}: {reply_e}")

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start, block=False))