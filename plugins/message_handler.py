async def handle_message(update: Update, context: CallbackContext) -> None:
    if update.effective_chat.type == 'private':
        return

    user = update.effective_user
    user_id = str(user.id)
    message_text = update.message.text or update.message.caption or ""

    # Skip low-effort messages
    if not message_text or len(message_text.strip()) < 5:
        return

    # Record and check for spam
    await db.record_message(user_id, message_text)
    if await db.is_spam(user_id, message_text):
        logger.info(f"Spam detected from user {user_id}: {message_text[:20]}...")
        return

    await db.increment_user_message_count(user_id, user.first_name)