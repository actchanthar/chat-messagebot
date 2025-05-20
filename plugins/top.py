from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database import db
import logging

# Configure logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the top 10 users by invite count."""
    user_id = str(update.effective_user.id)
    logger.info(f"Top command by user {user_id}")

    async with aiosqlite.connect("users.db") as conn:
        cursor = await conn.execute("""
            SELECT user_id, name, invite_count 
            FROM users 
            ORDER BY invite_count DESC 
            LIMIT 10
        """)
        top_users = await cursor.fetchall()

    if not top_users:
        await update.message.reply_text("No users found.")
        return

    message = "🏆 Top 10 Users by Invites:\n\n"
    for i, (user_id, name, invite_count) in enumerate(top_users, 1):
        message += f"{i}. {name} - {invite_count} invites\n"
    
    await update.message.reply_text(message)
    logger.info("Sent top users list")

# Add handler to application (example)
def add_handlers(application):
    application.add_handler(CommandHandler("top", top))