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
        [InlineKeyboardButton("Withdrawal", callback_data="withdraw")]
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
                    "/help - ဤစာကိုပြရန်"
                )
            )
            logger.info(f"Help shown for user {user_id}")
        elif data == "withdraw":
            if update.effective_chat.type != "private":
                logger.info(f"Ignoring withdraw request in group chat {chat_id}")
                return
            user = await db.get_user(user_id)
            if not user or user['balance'] < config.WITHDRAWAL_THRESHOLD:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"ထုတ်ယူရန်အတွက် အနည်းဆုံး {config.WITHRAWAL_THRESHOLD} {config.CURRENCY} လိုအပ်ပါသည်။"
                )
                return
            is_subscribed = await check_force_sub(context.bot, user_id, config.CHANNEL_ID)
            if not is_subscribed:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"ထုတ်ယူရန်အတွက် {config.CHANNEL_USERNAME} သို့ဝင်ရောက်ပါ။\nထို့နောက် ထပ်မံကြိုးစားပါ။"
                )
                return
            context.user_data["withdrawal"] = {"amount": user["balance"]}
            keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in config.PAYMENT_METHODS]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=chat_id,
                text="ငွေထုတ်ယူရန်နည်းလမ်းရွေးချယ်ပါ:",
                reply_markup=reply_markup
            )
            logger.info(f"Withdrawal initiated for user {user_id}, moving to PAYMENT_METHOD state")
            return PAYMENT_METHOD

    except Exception as e:
        logger.error(f"Error in button callback for user {user_id}: {str(e)}")
        await context.bot.send_message(chat_id=chat_id, text="An error occurred. Please try again later.")

async def handle_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    logger.info(f"Entering handle_payment_details for user {user_id} in chat {chat_id}, context: {context.user_data}")

    if update.effective_chat.type != "private":
        logger.info(f"Ignoring payment details in group chat {chat_id}")
        return ConversationHandler.END

    if "withdrawal" not in context.user_data or "method" not in context.user_data["withdrawal"]:
        await update.message.reply_text(
            "ကျေးဇူးပြု၍ /withdraw ဖြင့် ထုတ်ယူမှုစတင်ပါ။"
        )
        logger.info(f"No withdrawal context for user {user_id}")
        return ConversationHandler.END

    method = context.user_data["withdrawal"]["method"]
    amount = context.user_data["withdrawal"]["amount"]
    text = update.message.text.strip() if update.message.text else ""
    photo = update.message.photo[-1] if update.message.photo else None

    logger.info(f"Processing payment details for user {user_id}, method: {method}, text: '{text}', photo: {bool(photo)}")

    if not text and not photo:
        await update.message.reply_text(
            "ကျေးဇူးပြု၍ သင့်အကောင့်အသေးစိတ်အချက်အလက်များ သို့မဟုတ် QR ကုဒ်ပေးပို့ပါ။"
        )
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
        "သင့်ငွေထုတ်ယူမှုတောင်းဆိုမှုကို အက်ဒမင်ထံပေးပို့ပြီးပါပြီ။ လုပ်ဆောင်ပြီးသည်နှင့် အကြောင်းကြားပါမည်။"
    )
    context.user_data.pop("withdrawal", None)
    logger.info(f"Withdrawal request processed for user {user_id}")
    return ConversationHandler.END

async def cancel_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    context.user_data.pop("withdrawal", None)
    await update.message.reply_text("Withdrawal process cancelled. Use /withdraw to start again.")
    logger.info(f"Withdrawal process cancelled for user {user_id} in chat {chat_id}")
    return ConversationHandler.END

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
    logger.info(f"Unhandled message from user {user_id} in chat {chat_id}: text={update.message.text}, photo={update.message.photo}")

def register_handlers(application):
    # Register /start command
    application.add_handler(CommandHandler("start", start))
    
    # Conversation handler for withdrawal process
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback, pattern="^withdraw$")],
        states={
            PAYMENT_METHOD: [CallbackQueryHandler(button_callback, pattern="^payment_.*$")],
            PAYMENT_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND | filters.PHOTO, handle_payment_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel_withdrawal)],
    )
    application.add_handler(conv_handler)
    
    # Handle all other button callbacks outside conversation
    application.add_handler(CallbackQueryHandler(button_callback, pattern="^(balance|top|help)$"))
    
    # Fallback handler to debug unhandled messages
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, debug_unhandled_message), group=1)
    
    logger.info("Registered start command, conversation handler, button callbacks, and debug handler")