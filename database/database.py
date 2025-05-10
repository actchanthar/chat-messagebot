from Levenshtein import ratio

async def is_spam(self, user_id, text):
    text_hash = hashlib.md5(text.encode()).hexdigest()
    cutoff_time = datetime.now() - timedelta(seconds=self.time_window)

    # Check for exact duplicates
    count = await self.messages_collection.count_documents({
        "user_id": user_id,
        "text_hash": text_hash,
        "timestamp": {"$gt": cutoff_time}
    })
    if count >= self.spam_threshold:
        return True

    # Check for near-duplicates
    recent_messages = await self.messages_collection.find({
        "user_id": user_id,
        "timestamp": {"$gt": cutoff_time}
    }).to_list(length=10)
    for msg in recent_messages:
        stored_text = await self.get_message_text(msg["text_hash"])  # Assume you store original text
        if ratio(text, stored_text) > 0.9:  # 90% similarity
            return True

    return False