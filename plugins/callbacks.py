from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler, filters
from database.database import db
import config
import logging

logger = logging.getLogger(__name__)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    data = query.data

    try:
        if data == "balance":
            user = await db.get_user(user_id)
            if not user:
                await db.create_user(user_id, query.from_user.first_name)
                user = await db.get_user(user_id)
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"မင်္ဂလာပါ {user['name']}!\n"
                    f"စာတိုများ: {user['messages']}\n"
                    f"လက်ကျန်: {user['balance']} {config.CURRENCY}"
                )
            )
        elif data == "top":
            top_users = await db.get_top_users()
            if not top_users:
                await context.bot.send_message(
                    chat_id=user_id,
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
                chat_id=user_id,
                text=message
            )
        elif data == "help":
            await context.bot.send_message(
                chat_id=user_id,
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
        elif data == "withdraw":
            if update.effective_chat.type != "private":
                logger.info(f"Ignoring withdraw request in group chat {update.effective_chat.id}")
                return
            user = await db.get_user(user_id)
            if not user or user['balance'] < config.WITHDRAWAL_THRESHOLD:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"ထုတ်ယူရန်အတွက် အနည်းဆုံး {config.WITHDRAWAL_THRESHOLD} {config.CURRENCY} လိုအပ်ပါသည်။"
                )
                return

            is_subscribed = await check_force_sub(context.bot, user_id, config.CHANNEL_ID)
            if not is_subscribed:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"ထုတ်ယူရန်အတွက် {config.CHANNEL_USERNAME} သို့ဝင်ရောက်ပါ။\nထို့နောက် ထပ်မံကြိုးစားပါ။"
                )
                return

            context.user_data["withdrawal"] = {"amount": user["balance"]}
            keyboard = [[InlineKeyboardButton(method, callback_data=f"payment_{method}")] for method in config.PAYMENT_METHODS]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=user_id,
                text="ငွေထုတ်ယူရန်နည်းလမ်းရွေးချယ်ပါ:",
                reply_markup=reply_markup
            )
            logger.info(f"Withdrawal initiated for user {user_id}")
        elif data.startswith("payment_"):
            if update.effective_chat.type != "private":
                logger.info(f"Ignoring payment method selection in group chat {update.effective_chat.id}")
                return
            method = data.replace("payment_", "")
            if "withdrawal" not in context.user_data:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="ကျေးဇူးပြု၍ /withdraw ဖြင့် ထုတ်ယူမှုစတင်ပါ။"
                )
                return

            context.user_data["withdrawal"]["method"] = method
            if method == "KBZ Pay":
                await context.bot.send_message(
                    chat_id=user_id,
                    text="QR ကုဒ် သို့မဟုတ် အကောင့်အသေးစိတ်အချက်အလက်များ ပေးပို့ပါ (ဥပမာ: 09123456789 ZAYAR KO KO MIN ZAW)။"
                )
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"{method} အကောင့်အသေးစိတ်အချက်အလက်များ ပေးပို့ပါ။"
                )
            logger.info(f"Payment method {method} selected for user {user_id}")
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
                        text=f"သင့်ငွေထုတ်ယူမှု {amount} {config.CURRENCY} ကို အတည်ပြုပြီးပါသည်။ လက်ကျန်: {(user['balance'] - amount)} {config.CURRENCY}"
                    )
                    del context.user_data["pending_withdrawals"][approved_user_id]
                logger.info(f"Withdrawal approved for user {approved_user_id}, amount: {amount}")
        elif data.startswith("withdraw_reject_"):
            rejected_user_id = data.replace("withdraw_reject_", "")
            if rejected_user_id in context.user_data.get("pending_withdrawals", {}):
                await context.bot.send_message(
                    chat_id=rejected_user_id,
                    text="သင့်ငွေထုတ်ယူမှုတောင်းဆိုမှုကို ပယ်ချခံလိုက်ရပါသည်။"
                )
                del context.user_data["pending_withdrawals"][rejected_user_id]
                logger.info(f"Withdrawal rejected for user {rejected_user_id}")

    except Exception as e:
        logger.error(f"Error in button callback for user {user_id}: {e}")

async def handle_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        logger.info(f"Ignoring payment details in group chat {update.effective_chat.id}")
        return

    user_id = str(update.effective_user.id)
    logger.info(f"Checking withdrawal context for user {user_id}: {context.user_data.get('withdrawal')}")
    
    if "withdrawal" not in context.user_data or "method" not in context.user_data["withdrawal"]:
        await update.message.reply_text(
            "ကျေးဇူးပြု၍ /withdraw ဖြင့် ထုတ်ယူမှုစတင်ပါ။"
        )
        logger.info(f"No withdrawal context for user {user_id}")
        return

    method = context.user_data["withdrawal"]["method"]
    amount = context.user_data["withdrawal"]["amount"]
    text = update.message.text
    photo = update.message.photo[-1] if update.message.photo else None

    logger.info(f"Received payment details for user {user_id}, method: {method}, text: {text}, photo: {bool(photo)}")

    if not text and not photo:
        await update.message.reply_text(
            "ကျေးဇူးပြု၍ သင့်အကောင့်အသေးစိတ်အချက်အလက်များ သို့မဟုတ် QR ကုဒ်ပေးပို့ပါ။"
        )
        logger.info(f"No text or photo provided by user {user_id}")
        return

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

async def check_force_sub(bot, user_id, channel_id):
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id}: {e}")
        return False

def register_handlers(application):
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(
        (filters.TEXT & ~filters.COMMAND) | filters.PHOTO,
        handle_payment_details
    ))
    logger.info("Registered callback and payment details handlers")