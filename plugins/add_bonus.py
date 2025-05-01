from telegram import Update
from telegram.ext import CallbackContext
from config import ADMIN_IDS, LOG_CHANNEL
from database.database import get_user, update_user

async def add_bonus(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Restrict command to admins
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("ဒီညွှန်ကြားချက်ကို အက်ဒမင်များသာ အသုံးပြုနိုင်ပါတယ်။")
        return

    # Check command format: /add_bonus <user_id> <amount>
    if not context.args or len(context.args) != 2:
        await update.message.reply_text(
            "ကျေးဇူးပြုပြီး အောက်ပါပုံစံဖြင့် ထည့်ပါ�。\n"
            "ဥပမာ: /add_bonus 987654321 50"
        )
        return

    try:
        target_user_id = int(context.args[0])
        bonus_amount = int(context.args[1])
        if bonus_amount <= 0:
            await update.message.reply_text("ဘိုနပ်စ်ပမာဏသည် ၀ ထက်ကြီးရပါမည်။")
            return
    except ValueError:
        await update.message.reply_text("User ID နှင့် ပမာဏသည် ဂဏန်းများဖြစ်ရပါမည်။")
        return

    # Get the user's current balance
    user = await get_user(target_user_id, chat_id)
    current_balance = user.get("balance", 0) if user else 0

    # Update the user's balance with the bonus
    new_balance = current_balance + bonus_amount
    await update_user(target_user_id, chat_id, {"balance": new_balance})

    # Notify the user in the group
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🎉 @{update.effective_user.username} မှ ဘိုနပ်စ် {bonus_amount} ကျပ် ပေးအပ်ခဲ့ပါတယ်။\n"
             f"သင့်လက်ကျန်ငွေ: {new_balance} ကျပ်"
    )

    # Log the bonus in the log channel
    await context.bot.send_message(
        chat_id=LOG_CHANNEL,
        text=f"🎁 Bonus Added\n"
             f"Admin: @{update.effective_user.username} (ID: {user_id})\n"
             f"User ID: {target_user_id}\n"
             f"Amount: {bonus_amount} ကျပ်\n"
             f"Group: {chat_id}"
    )