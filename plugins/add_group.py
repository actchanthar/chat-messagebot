async def add_group(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("ဒီညွှန်ကြားချက်ကို အက်ဒမင်များသာ အသုံးပြုနိုင်ပါတယ်။")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "ကျေးဇူးပြုပြီး အောက်ပါပုံစံဖြင့် ထည့်ပါ။\n"
            "ဥပမာ: /addgroup -100123456789 123456789 987654321"
        )
        return

    try:
        new_chat_id = int(context.args[0])
        admin_ids = [int(admin_id) for admin_id in context.args[1:]]
    except ValueError:
        await update.message.reply_text("Chat ID နှင့် Admin ID များသည် ဂဏန်းများဖြစ်ရပါမည်။")
        return

    await add_chat_group(new_chat_id, admin_ids)

    await update.message.reply_text(
        f"Chat Group {new_chat_id} ကို အောင်မြင်စွာ ထည့်ပြီးပါပြီ။\n"
        f"အက်ဒမင်များ: {', '.join([str(admin_id) for admin_id in admin_ids])}"
    )