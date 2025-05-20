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
                inviter = await db.get_user(inviter_id)
                if inviter:
                    inviter_invites = inviter.get("invite_count", 0) + 1
                    logger.info(f"Before update: {inviter_id} invite_count={inviter.get('invite_count', 0)}")
                    await db.update_user(inviter_id, {
                        "invite_count": inviter_invites,
                        "invited_users": inviter.get("invited_users", []) + [user_id]
                    })
                    updated_inviter = await db.get_user(inviter_id)
                    logger.info(f"After update: {inviter_id} invite_count={updated_inviter.get('invite_count', 0)}")
                    try:
                        await context.bot.send_message(
                            inviter_id,
                            f"🎉 A new user has joined via your referral! You now have {inviter_invites} invites.\n"
                            f"Share this link to invite more: https://t.me/{context.bot.username}?start=referral_{inviter_id}"
                        )
                        logger.info(f"Sent referral notification to {inviter_id}")
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
            elif inviter_id and inviter_id != user_id and not user.get("referral_rewarded", False):
                logger.info(f"Processing channel join reward for user {user_id} invited by {inviter_id}")
                inviter = await db.get_user(inviter_id)
                if inviter:
                    inviter_balance = inviter.get("balance", 0) + 25
                    inviter_invites = inviter.get("invite_count", 0)
                    try:
                        await db.update_user(inviter_id, {"balance": inviter_balance})
                        updated_inviter = await db.get_user(inviter_id)
                        inviter_invites = updated_inviter.get("invite_count", 0)
                        await context.bot.send_message(
                            inviter_id,
                            f"Your invite joined all channels! +25 kyat. Total invites: {inviter_invites}"
                        )
                        await db.update_user(user_id, {
                            "balance": user.get("balance", 0) + 50,
                            "referral_rewarded": True
                        })
                        await update.message.reply_text("You joined all channels via referral! +50 kyat.")
                        logger.info(f"Reward applied: {inviter_id} +25 kyat, {user_id} +50 kyat, inviter invites: {inviter_invites}")
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

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        user_id = str(query.from_user.id)
        logger.info(f"Balance check requested by user {user_id}")
        try:
            user = await db.get_user(user_id)
            if user:
                balance = user.get("balance", 0)
                await query.message.reply_text(f"Your current balance is {balance} kyat.")
                logger.info(f"Balance {balance} sent to user {user_id}")
            else:
                await query.message.reply_text("User not found. Please start the bot with /start.")
                logger.error(f"User {user_id} not found for balance check")
        except Exception as e:
            logger.error(f"Error checking balance for {user_id}: {e}")
            await query.message.reply_text("An error occurred while checking your balance. Please try again later.")
        await query.answer()

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        user_id = str(query.from_user.id)
        logger.info(f"Withdraw requested by user {user_id}")
        try:
            user = await db.get_user(user_id)
            if not user:
                await query.message.reply_text("User not found. Please start the bot with /start.")
                logger.error(f"User {user_id} not found for withdraw")
                await query.answer()
                return

            invite_count = user.get("invite_count", 0)
            balance = user.get("balance", 0)
            withdrawn_today = user.get("withdrawn_today", 0)
            last_withdrawal = user.get("last_withdrawal")
            invite_threshold = await db.get_setting("invite_threshold", 15)
            min_balance = await db.get_setting("min_balance", 1000)  # Minimum balance for withdrawal
            daily_limit = await db.get_setting("daily_limit", 5000)  # Daily withdrawal limit

            # Check invite threshold
            if invite_count < invite_threshold:
                await query.message.reply_text(
                    f"You need at least {invite_threshold} invites to withdraw. "
                    f"You currently have {invite_count} invites."
                )
                logger.info(f"User {user_id} failed withdraw: insufficient invites ({invite_count}/{invite_threshold})")
                await query.answer()
                return

            # Check balance
            if balance < min_balance:
                await query.message.reply_text(
                    f"Your balance ({balance} kyat) is below the minimum withdrawal amount of {min_balance} kyat."
                )
                logger.info(f"User {user_id} failed withdraw: insufficient balance ({balance}/{min_balance})")
                await query.answer()
                return

            # Check daily withdrawal limit
            current_time = datetime.utcnow()
            if last_withdrawal and last_withdrawal.date() == current_time.date():
                if withdrawn_today >= daily_limit:
                    await query.message.reply_text(
                        f"You've reached the daily withdrawal limit of {daily_limit} kyat. Try again tomorrow."
                    )
                    logger.info(f"User {user_id} failed withdraw: daily limit reached ({withdrawn_today}/{daily_limit})")
                    await query.answer()
                    return
                amount_to_withdraw = min(balance, daily_limit - withdrawn_today)
            else:
                amount_to_withdraw = min(balance, daily_limit)
                withdrawn_today = 0  # Reset if it's a new day

            # Process withdrawal
            new_balance = balance - amount_to_withdraw
            await db.update_user(user_id, {
                "balance": new_balance,
                "withdrawn_today": withdrawn_today + amount_to_withdraw,
                "last_withdrawal": current_time
            })
            await query.message.reply_text(
                f"Withdrawal successful! You withdrew {amount_to_withdraw} kyat. "
                f"Your new balance is {new_balance} kyat."
            )
            logger.info(f"User {user_id} withdrew {amount_to_withdraw} kyat, new balance: {new_balance}")

            # Notify admin (optional)
            try:
                await context.bot.send_message(
                    ADMIN_ID,
                    f"User {user_id} withdrew {amount_to_withdraw} kyat. Remaining balance: {new_balance} kyat."
                )
            except Exception as e:
                logger.error(f"Failed to notify admin about withdrawal for {user_id}: {e}")

        except Exception as e:
            logger.error(f"Error processing withdraw for {user_id}: {e}")
            await query.message.reply_text("An error occurred while processing your withdrawal. Please try again later.")
        await query.answer()

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