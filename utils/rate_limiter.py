import asyncio
import logging
from telegram.error import RetryAfter, TelegramError

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_message_rate_limited(bot, chat_id, text, **kwargs):
    """Send a message with rate limiting and error handling."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await bot.send_message(chat_id=chat_id, text=text, **kwargs)
        except RetryAfter as e:
            logger.warning(f"Rate limit hit, retrying after {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after)
        except TelegramError as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            if attempt == max_retries - 1:
                return None
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Unexpected error sending message to {chat_id}: {e}")
            return None
    return None

async def send_messages_batch(bot, messages, batch_size=30, delay=1):
    """Send messages in batches with delays to avoid rate limits."""
    for i in range(0, len(messages), batch_size):
        batch = messages[i:i + batch_size]
        tasks = []
        for chat_id, text, kwargs in batch:
            tasks.append(send_message_rate_limited(bot, chat_id, text, **kwargs))
        await asyncio.gather(*tasks, return_exceptions=True)
        if i + batch_size < len(messages):
            await asyncio.sleep(delay)
