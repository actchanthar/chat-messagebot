from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
    CommandHandler
)
from database.database import db
import config
import logging

logger = logging.getLogger(__name__)

# States for ConversationHandler
PAYMENT_METHOD, PAYMENT_DETAILS = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Received /start command from user {user_id} in chat {chat_id}")
    
    user = await db.get_user(user_id)
    if not user:
        await db.create_user(user_id, update.effective_user.first_name)
        user = await db.get_user(user_id)
    
    keyboard = [
        [InlineKeyboardButton("Balance", callback_data="balance")],
        [InlineKeyboardButton("Top", callback_data="top")],
        [InlineKeyboardButton("Help", callback_data="help")],
        [InlineKeyboardButton("ထုတ်ယူရန်", callback_data="withdraw")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "မင်္ဂလာပါ!\n"
            f"စာတိုများ: {user['messages']}\n"
            f"လက်ကျန်: {user['balance']} {config.CURRENCY}\n"
            "Choose an option:"
        ),
        reply_markup=reply_markup
    )
    logger.info(f"Successfully sent /start response to user {user_id} in chat {chat_id}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    chat_id = str(query.message.chat_id)
    data = query.data
    logger.info(f"Button callback received: user {user_id}, chat {chat_id}, data: {data}, context: {context.user_data}")

    try:
        if data == "balance":
            user = await db.get_user(user_id)
            if not user:
                await db.create_user(user_id, query.from_user.first_name)
                user = await db.get_user(user_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"မင်္ဂလာပါ {user['name']}!\n"
                    f"စာတိုများ: {user['messages']}\n"
                    f"လက်ကျန်: {user['balance']} {config.CURRENCY}"
                )
            )
            logger.info(f"Balance checked for user {user_id}")
        elif data == "top":
            top_users = await db.get_top_users()
            if not top_users:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="အဆင့်သတ်မှတ်ချက်မရှိသေးပါ။"
                )
                return
            message = "🏆 ထိပ်တန်းအသုံးပြုသူများ 🏆\n"
            for i, user in enumerate(top_users, 1):
                message += f"{i}. {user['name']}: {user['messages']} စာတို၊ {user['balance']} {config.CURRENCY}\n"
            total_messages = sum(user['messages'] for user in top_users)
            total_balance = sum(user['balance'] for user in top_users)
            message += f"\nစုစုပေါင်းစာတိုများ: {total_messages}\nစုစုပေါင်းဆုလာဘ်: {total_balance} {config.CURRENCY}"
            await context.bot.send_message(
                chat_id=chat_id,
                text=message
            )
            logger.info(f"Top users shown for user {user_id}")
        elif data == "help":
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "တစ်စာတိုလျှင် ၁ ကျပ်ရရှိမည်။\n"
                    "ထုတ်ယူရန်အတွက် ကျွန်ုပ်တို့၏ချန်နယ်သို့ဝင်ရောက်ပါ။\n\n"
                    "အမိန့်များ:\n"
                    "/balance - ဝင်ငွေစစ်ဆေးရန်\n"
                    "/top - ထိပ်တန်းအသုံးပြုသူများကြည့်ရန်\n"
                    "/withdraw - ထုတ်ယူရန်တောင်းဆိုရန်\n"
                    "/force_withdraw - ငွေထုတ်ခြင်းကို အတင်းစတင်ရန်\n"
                    "/help - ဤစာကိုပြရန်\n"
                    "/reset - Reset withdrawal process\n"
                    "/debug - Check current state\n"
                    "/force_payment_details - Force payment details state"
                )
            )
            logger.info(f"Help shown for user {user_id}")
        elif data == "withdraw":
            if update.effective_chat.type != "private":
                logger.info(f"Ignoring withdraw request in group chat {chat_id}")
                await query.message.reply_text("This action is only available in private chat.")
                return
            user = await db.get_user(user_id)
            if not user:
                await db.create_user(user_id, query.from_user.first_name)
                user = await db.get_user(user_id)
            if user['balance'] < config.WITHDRAWAL_THRESHOLD:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"ထုတ်ယူရန်အတွက် အနည်းဆုံး {config.WITHDRAWAL_THRESHOLD} {config.CURRENCY} လိုအပ်ပါသည်။"
                )
                logger.info(f"Insufficient balance for user {user_id}: {user['balance']}")
                return
            try:
                is_subscribed = await check_force_sub(context.bot, user_id, config.CHANNEL_ID)
                if not is_subscribed:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"ထုတ်ယူရန်အတွက် {config.CHANNEL_USERNAME} သို့ဝင်ရောက်ပါ။\nထို့နောက် ထပ်မံကြိုးစားပါ။"
                    )
                    logger.info(f"User {user_id} not subscribed to {config.CHANNEL_USERNAME}")
                    return
            except Exception as e:
                logger.error(f"Subscription check failed for user {user_id}: {str(e)}")
                await context.bot.send_message(chat_id=chat_id, text="Subscription check failed. Please try again later.")
                return
            # Clear existing data before starting a new withdrawal
            context.user_data.clear()
            context.user_data["withdrawal"] = {"amount": user["balance"]}
            context.user_data["state"] = PAYMENT_METHOD
            keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in config.PAYMENT_METHODS]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=chat_id,
                text="Choose a payment method:",
                reply_markup=reply_markup
            )
            logger.info(f"Withdrawal initiated for user {user_id}, state set to PAYMENT_METHOD")
            return PAYMENT_METHOD
        elif data.startswith("payment_"):
            if update.effective_chat.type != "private":
                logger.info(f"Ignoring payment method selection in group chat {chat_id}")
                await query.message.reply_text("This action is only available in private chat.")
                return
            method = data.replace("payment_", "")
            logger.info(f"Payment method {method} selected by user {user_id}")
            if "withdrawal" not in context.user_data:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Please start the withdrawal process with /withdraw."
                )
                logger.info(f"No withdrawal context for user {user_id}")
                return
            context.user_data["withdrawal"]["method"] = method
            context.user_data["state"] = PAYMENT_DETAILS
            if method == "KBZ Pay":
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Please send your QR code or account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW)."
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Please send your {method} account details."
                )
            logger.info(f"Payment method {method} confirmed for user {user_id}, state set to PAYMENT_DETAILS")
            return PAYMENT_DETAILS
        elif data.startswith("withdraw_approve_"):
            approved_user_id = data.replace("withdraw_approve_", "")
            if approved_user_id in context.user_data.get("pending_withdrawals", {}):
                withdrawal = context.user_data["pending_withdrawals"][approved_user_id]
                amount = withdrawal["amount"]
                user = await db.get_user(approved_user_id)
                if user and user["balance"] >= amount:
                    await db.update_user(approved_user_id, balance=user["balance"] - amount)
                    await context.bot.send_message(
                        chat_id=approved_user_id,
                        text=f"Your withdrawal of {amount} {config.CURRENCY} has been approved. Remaining balance: {(user['balance'] - amount)} {config.CURRENCY}"
                    )
                    # Send announcement to the group
                    username = user.get("username", user["name"])  # Use username if available, else first name
                    mention = f"@{username}" if username else user["name"]
                    group_message = f"{mention} သူက ငွေ {amount} ကျပ်ထုတ်ခဲ့သည် ချိုချဉ်ယ်စားပါ"
                    try:
                        await context.bot.send_message(
                            chat_id=config.GROUP_CHAT_ID,
                            text=group_message
                        )
                        logger.info(f"Sent withdrawal announcement to group {config.GROUP_CHAT_ID} for user {approved_user_id}")
                    except Exception as e:
                        logger.error(f"Failed to send announcement to group {config.GROUP_CHAT_ID}: {str(e)}")
                    del context.user_data["pending_withdrawals"][approved_user_id]
                logger.info(f"Withdrawal approved for user {approved_user_id}, amount: {amount}")
        elif data.startswith("withdraw_reject_"):
            rejected_user_id = data.replace("withdraw_reject_", "")
            if rejected_user_id in context.user_data.get("pending_withdrawals", {}):
                await context.bot.send_message(
                    chat_id=rejected_user_id,
                    text="Your withdrawal request has been rejected."
                )
                del context.user_data["pending_withdrawals"][rejected_user_id]
                logger.info(f"Withdrawal rejected for user {rejected_user_id}")

    except Exception as e:
        logger.error(f"Error in button callback for user {user_id}: {str(e)}")
        await context.bot.send_message(chat_id=chat_id, text="An error occurred. Please try again later.")
        return ConversationHandler.END

async def handle_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message = update.message if update.message else None
    current_state = context.user_data.get("state", "Unknown")
    logger.info(f"Entering handle_payment_details for user {user_id} in chat {chat_id}, state: {current_state}, message: {message}, context: {context.user_data}")

    if update.effective_chat.type != "private":
        logger.info(f"Ignoring payment details in group chat {chat_id}")
        return ConversationHandler.END

    if "withdrawal" not in context.user_data or "method" not in context.user_data["withdrawal"]:
        await update.message.reply_text(
            "Please start the withdrawal process with /withdraw."
        ) if update.message else None
        logger.info(f"No withdrawal context for user {user_id}")
        return ConversationHandler.END

    method = context.user_data["withdrawal"]["method"]
    amount = context.user_data["withdrawal"]["amount"]
    text = message.text.strip() if message and message.text else ""
    photo = message.photo[-1] if message and message.photo else None

    logger.info(f"Processing payment details for user {user_id}, method: {method}, text: '{text}', photo: {bool(photo)}")

    if not text and not photo:
        await update.message.reply_text(
            "Please send your account details or QR code."
        ) if update.message else None
        logger.info(f"No valid input from user {user_id}")
        return PAYMENT_DETAILS

    username = update.effective_user.username or update.effective_user.first_name
    profile_info = (
        f"Withdrawal Request\n"
        f"User: @{username}\n"
        f"User ID: {user_id}\n"
        f"Amount: {amount} {config.CURRENCY}\n"
        f"Method: {method}\n"
        f"Details:\n"
    )
    if text:
        profile_info += f"Text: {text}\n"

    context.user_data.setdefault("pending_withdrawals", {})[user_id] = {
        "amount": amount,
        "method": method,
        "details": text if text else "Photo provided"
    }

    keyboard = [
        [
            InlineKeyboardButton("Approve", callback_data=f"withdraw_approve_{user_id}"),
            InlineKeyboardButton("Reject", callback_data=f"withdraw_reject_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for admin_id in config.ADMIN_IDS:
        if admin_id:
            try:
                if photo:
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=photo.file_id,
                        caption=profile_info,
                        reply_markup=reply_markup
                    )
                else:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=profile_info,
                        reply_markup=reply_markup
                    )
                logger.info(f"Sent withdrawal request to admin {admin_id} for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")

    await update.message.reply_text(
        "Your withdrawal request has been sent to the admin. You’ll be notified once it’s processed."
    ) if update.message else None
    # Fully clear all data after processing
    context.user_data.clear()
    logger.info(f"Withdrawal request processed for user {user_id}, all data cleared")
    return ConversationHandler.END

async def force_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    if update.effective_chat.type != "private":
        await update.message.reply_text("This command is only available in private chat.")
        return
    user = await db.get_user(user_id)
    if not user:
        await db.create_user(user_id, update.effective_user.first_name)
        user = await db.get_user(user_id)
    if user['balance'] < config.WITHDRAWAL_THRESHOLD:
        await update.message.reply_text(
            f"ထုတ်ယူရန်အတွက် အနည်းဆုံး {config.WITHDRAWAL_THRESHOLD} {config.CURRENCY} လိုအပ်ပါသည်။"
        )
        logger.info(f"Insufficient balance for user {user_id}: {user['balance']}")
        return
    try:
        is_subscribed = await check_force_sub(context.bot, user_id, config.CHANNEL_ID)
        if not is_subscribed:
            await update.message.reply_text(
                f"ထုတ်ယူရန်အတွက် {config.CHANNEL_USERNAME} သို့ဝင်ရောက်ပါ။\nထို့နောက် ထပ်မံကြိုးစားပါ။"
            )
            logger.info(f"User {user_id} not subscribed to {config.CHANNEL_USERNAME}")
            return
    except Exception as e:
        logger.error(f"Subscription check failed for user {user_id}: {str(e)}")
        await update.message.reply_text("Subscription check failed. Please try again later.")
        return
    # Clear any existing data and start fresh
    context.user_data.clear()
    context.user_data["withdrawal"] = {"amount": user["balance"]}
    context.user_data["state"] = PAYMENT_METHOD
    keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in config.PAYMENT_METHODS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Choose a payment method:",
        reply_markup=reply_markup
    )
    logger.info(f"Forced withdrawal initiated for user {user_id}, state set to PAYMENT_METHOD")

async def force_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    if update.effective_chat.type != "private":
        await update.message.reply_text("This command is only available in private chat.")
        return
    if "withdrawal" not in context.user_data or "method" not in context.user_data["withdrawal"]:
        await update.message.reply_text("Please start the withdrawal process with /withdraw first.")
        return
    context.user_data["state"] = PAYMENT_DETAILS
    method = context.user_data["withdrawal"]["method"]
    if method == "KBZ Pay":
        await update.message.reply_text("Please send your QR code or account details (e.g., 09123456789 ZAYAR KO KO MIN ZAW).")
    else:
        await update.message.reply_text(f"Please send your {method} account details.")
    logger.info(f"Forced PAYMENT_DETAILS state for user {user_id} in chat {chat_id}")

async def catch_missed_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    if update.effective_chat.type != "private":
        return
    if context.user_data.get("state") == PAYMENT_DETAILS:
        logger.info(f"Caught missed message for user {user_id} in chat {chat_id}, redirecting to handle_payment_details")
        await handle_payment_details(update, context)

async def cancel_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    context.user_data.clear()
    await update.message.reply_text("Withdrawal process cancelled. Use /withdraw to start again.") if update.message else None
    logger.info(f"Withdrawal process cancelled for user {user_id} in chat {chat_id}")
    return ConversationHandler.END

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    context.user_data.clear()
    logger.info(f"Reset state for user {user_id} in chat {chat_id}")
    await update.message.reply_text("State has been reset. Use /withdraw to start again.")
    return ConversationHandler.END

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    state = context.user_data.get("state", "Unknown")
    withdrawal = context.user_data.get("withdrawal", {})
    logger.info(f"Debug for user {user_id} in chat {chat_id}: State={state}, Withdrawal={withdrawal}")
    await update.message.reply_text(
        f"Debug Info:\nState: {state}\nWithdrawal: {withdrawal}"
    )

async def check_force_sub(bot, user_id, channel_id):
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id}: {e}")
        return False

async def debug_unhandled_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    message = update.message if update.message else None
    logger.info(f"Debug unhandled message: user {user_id} in chat {chat_id}, chat type: {update.effective_chat.type}, text={message.text if message and message.text else 'None'}, photo={message.photo if message else 'None'}, context: {context.user_data}")

def register_handlers(application):
    # Register new commands
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("debug", debug))
    application.add_handler(CommandHandler("force_payment_details", force_payment_details))
    application.add_handler(CommandHandler("force_withdraw", force_withdraw))
    
    # Register /start command
    application.add_handler(CommandHandler("start", start))
    
    # Conversation handler for withdrawal process
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback, pattern="^withdraw$")],
        states={
            PAYMENT_METHOD: [CallbackQueryHandler(button_callback, pattern="^payment_.*$")],
            PAYMENT_DETAILS: [
                MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_payment_details),
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_payment_details),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_withdrawal)],
        per_chat=True,
        per_user=True,
    )
    application.add_handler(conv_handler, group=0)
    
    # Fallback to catch missed messages in private chats
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, catch_missed_messages), group=1)
    
    # Handle all other button callbacks outside conversation
    application.add_handler(CallbackQueryHandler(button_callback, pattern="^(balance|top|help|withdraw_approve_.*|withdraw_reject_.*)$"), group=2)
    
    # Fallback handler to debug unhandled messages
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, debug_unhandled_message), group=3)
    
    logger.info("Registered start command, conversation handler, button callbacks, reset, debug, force_payment_details, force_withdraw, and debug handler")