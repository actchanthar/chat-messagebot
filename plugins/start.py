from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Start command initiated by user {user_id} in chat {chat_id}")

    # Check for referral
    if context.args and context.args[0].isdigit():
        referrer_id = context.args[0]
        user = await db.get_user(user_id)
        if not user:
            try:
                user = await db.create_user(user_id, update.effective_user.full_name)
                if not user:
                    raise ValueError("User creation failed")
            except Exception as e:
                logger.error(f"Error creating user {user_id} during referral: {e}")
                await update.message.reply_text("Error creating your account. Please try again later.")
                return
            channels = await db.get_channels()
            all_joined = True
            for channel in channels:
                try:
                    member = await context.bot.get_chat_member(channel["channel_id"], user_id)
                    if member.status not in ["member", "administrator", "creator"]:
                        all_joined = False
                        break
                except Exception:
                    all_joined = False
                    break
            if all_joined:
                await db.increment_invite(referrer_id, user_id)
                try:
                    await context.bot.send_message(referrer_id, "You earned 25 kyat for a successful referral!")
                    await context.bot.send_message(user_id, "You earned 50 kyat for joining via referral!")
                except Exception as e:
                    logger.error(f"Error notifying referral: {e}")
            else:
                await update.message.reply_text("Please join all required channels to complete the referral.")
                return

    user = await db.get_user(user_id)
    if not user:
        try:
            user = await db.create_user(user_id, update.effective_user.full_name)
            if not user:
                raise ValueError("User creation failed")
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            await update.message.reply_text("Error creating your account. Please try again later.")
            return

    # Ensure referral_link exists
    referral_link = user.get("referral_link", f"https://t.me/ACTChatBot?start={user_id}")
    if "referral_link" not in user:
        await db.update_user(user_id, {"referral_link": referral_link})

    welcome_message = (
        "စာပို့ရင်း ငွေရှာမယ်:\n"
        f"Welcome to the Chat Bot, {update.effective_user.full_name}! 🎉\n\n"
        "Earn money by sending messages in the group! (3 messages = 1 kyat)\n"
        "အုပ်စုတွင် စာပို့ခြင်းဖြင့် ငွေရှာပါ (၃ စာတိုလျှင် ၁ ကျပ်)။\n\n"
        f"Your referral link: {referral_link}\n"
        "Invite friends to earn 25 kyat per successful invite!\n"
    )

    # Fetch top users by invites
    top_users = await db.get_top_users(10, sort_by="invites")
    if top_users and top_users[0].get("invites", 0) > 0:
        phone_bill_reward = await db.get_phone_bill_reward()
        welcome_message += (
            "🏆 Top Users by Invites:\n\n"
            f"(၇ ရက်တစ်ခါ Top 1-3 ရတဲ့လူကို {phone_bill_reward} မဲဖောက်ပေးပါတယ်):\n\n"
        )
        for i, user in enumerate(top_users, 1):
            invites = user.get("invites", 0)
            balance = user.get("balance", 0)
            welcome_message += f"{i}. <b>{user['name']}</b> - {invites} invites, {balance} kyat\n" if i <= 3 else f"{i}. {user['name']} - {invites} invites, {balance} kyat\n"

    # Fetch top users by messages
    top_users = await db.get_top_users(10, sort_by="messages")
    if top_users and top_users[0].get("group_messages", {}).get("-1002061898677", 0) > 0:
        phone_bill_reward = await db.get_phone_bill_reward()
        welcome_message += (
            "\n🏆 Top Users by Messages:\n\n"
            f"(၇ ရက်တစ်ခါ Top 1-3 ရတဲ့လူကို {phone_bill_reward} မဲဖောက်ပေးပါတယ်):\n\n"
        )
        for i, user in enumerate(top_users, 1):
            messages = user.get("group_messages", {}).get("-1002061898677", 0)
            balance = user.get("balance", 0)
            welcome_message += f"{i}. <b>{user['name']}</b> - {messages} msg, {balance} kyat\n" if i <= 3 else f"{i}. {user['name']} - {messages} msg, {balance} kyat\n"

    welcome_message += (
        "\nUse the buttons below to check your balance, withdraw, or join our group.\n"
        "သင့်လက်ကျန်ငွေ စစ်ဆေးရန်၊ သင့်ဝင်ငွေများကို ထုတ်ယူရန် သို့မဟုတ် ကျွန်ုပ်တို့၏ အုပ်စုသို့ ဝင်ရောက်ရန် အောက်ပါခလုတ်များကို အသုံးပြုပါ။"
    )

    keyboard = [
        [
            InlineKeyboardButton("Check Balance", callback_data="check_balance"),
            InlineKeyboardButton("Withdraw", callback_data="init_withdraw")
        ],
        [InlineKeyboardButton("Join Group", url="https://t.me/yourgroup")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="HTML")
    logger.info(f"Sent welcome message to user {user_id} in chat {chat_id}")

def register_handlers(application: Application):
    logger.info("Registering start handlers")
    application.add_handler(CommandHandler("start", start))