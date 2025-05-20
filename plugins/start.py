from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from database.database import db
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_ID = "5062124930"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    logger.info(f"Start command by user {user_id} in chat {chat_id}")
    logger.info(f"Context args: {context.args}")  # Log raw args for debugging

    user = await db.get_user(user_id)
    inviter_id = None

    # Handle referral
    if context.args and context.args[0].startswith("referral_"):
        inviter_id = context.args[0].replace("referral_", "")
        logger.info(f"Referral detected: user {user_id} invited by {inviter_id}")
        if not user:
            user = await db.create_user(user_id, update.effective_user.full_name)
            await db.update_user(user_id, {"inviter_id": inviter_id})
            logger.info(f"New user {user_id} created with inviter {inviter_id}")
            # Increment inviter's invite count
            if inviter_id and inviter_id != user_id:
                success = await db.add_referral(inviter_id, user_id)
                if success:
                    updated_inviter = await db.get_user(inviter_id)
                    inviter_invites = updated_inviter.get("invite_count", 0)
                    logger.info(f"Inviter {inviter_id} updated, current invite_count: {inviter_invites}")
                    try:
                        await context.bot.send_message(
                            inviter_id,
                            f"🎉 A new user has joined via your referral! You now have {inviter_invites} invites.\n"
                            f"Share this link to invite more: https://t.me/{context.bot.username}?start=referral_{inviter_id}"
                        )
                        logger.info(f"Sent referral notification to {inviter_id}")
                    except Exception as e:
                        logger.error(f"Failed to notify inviter {inviter_id}: {e}")
                else:
                    logger.warning(f"Failed to update inviter {inviter_id} invite_count")

    if not user:
        user = await db.create_user(user_id, update.effective_user.full_name)

    # Rest of the code remains unchanged (force-sub, rewards, welcome message) ...
    # Ensure to import datetime if not already present for withdrawal logic
    from datetime import datetime

    # [Existing force-sub and reward logic unchanged] ...

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

# [Existing check_balance and withdraw functions unchanged] ...

def register_handlers(application: Application):
    logger.info("Registering start, balance, and withdraw handlers")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(check_balance, pattern="^balance$"))
    application.add_handler(CallbackQueryHandler(withdraw, pattern="^withdraw$"))

if __name__ == "__main__":
    from telegram.ext import ApplicationBuilder
    application = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()
    register_handlers(application)
    application.run_polling()