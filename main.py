#!/usr/bin/env python3
import logging
from telegram.ext import Application, CommandHandler
from config import BOT_TOKEN
from database.database import db

# Import all plugins
from plugins import message_handler, balance, admin, broadcast, withdrawal, stats, help

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]  # Only console output, no log file
)
logger = logging.getLogger(__name__)

async def start_command(update, context):
    user_id = str(update.effective_user.id)
    user_name = {
        "first_name": update.effective_user.first_name or "",
        "last_name": update.effective_user.last_name or ""
    }
    
    # Check for referral
    referred_by = None
    if context.args and context.args[0].startswith("ref_"):
        referred_by = context.args[0][4:]
    
    user = await db.get_user(user_id)
    if not user:
        await db.create_user(user_id, user_name, referred_by)
        welcome_message = """
🎉 Welcome to Message Earning Bot!

💰 Earn money by chatting in approved groups
📝 3 messages = 1 kyat
🎯 Minimum withdrawal: 200 kyat
💸 Daily limit: 10,000 kyat

Commands:
/balance - Check your earnings
/stats - View detailed statistics  
/withdraw - Request withdrawal
/help - Get help

Start chatting in approved groups to earn! 💪
        """
    else:
        current_balance = user.get('balance', 0)
        welcome_message = f"Welcome back! Your balance: {int(current_balance)} kyat"
    
    await update.message.reply_text(welcome_message)

def main():
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add start command
    application.add_handler(CommandHandler("start", start_command))
    
    # Register all plugin handlers
    message_handler.register_handlers(application)
    balance.register_handlers(application)
    admin.register_handlers(application)
    broadcast.register_handlers(application)
    withdrawal.register_handlers(application)
    stats.register_handlers(application)
    help.register_handlers(application)
    
    logger.info("Message Earning Bot started successfully!")
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == '__main__':
    main()
